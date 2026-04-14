import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from yookassa import Configuration, Payment

from app.core.config import settings
from app.models.order import Order, OrderStatus
from app.models.subscription import Subscription, SubscriptionStatus
Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

logger = structlog.get_logger(__name__)

# Юридическое: тексты чеков (description, vat_code, payment_subject/payment_mode) должны
# соответствовать оферте и режиму НДС; изменения согласовать с бухгалтерией (54-ФЗ).


def parse_order_id_from_metadata(raw: object) -> int | None:
    """Безопасно извлекает order_id из metadata ЮKassa (строка, int и т.д.)."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    try:
        return int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        logger.warning("Invalid order_id in payment metadata", order_id_raw=repr(raw))
        return None


def parse_subscription_id_from_metadata(raw: object) -> int | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _payment_method_id_from_yookassa(payment_obj: dict) -> str | None:
    pm = payment_obj.get("payment_method")
    if not pm:
        return None
    if isinstance(pm, dict):
        return pm.get("id")
    return getattr(pm, "id", None)


class YookassaPaymentService:
    def __init__(self):
        self.return_url = settings.YOOKASSA_RETURN_URL

    async def create_payment(
        self,
        order_id: int,
        amount: Decimal,
        description: str,
        user_email: str,
        metadata: Optional[Dict] = None,
        *,
        save_payment_method: bool = False,
        idempotency_key: str | None = None,
    ) -> Dict[str, Any]:
        payment_data: Dict[str, Any] = {
            "amount": {"value": str(amount), "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": self.return_url},
            "capture": True,
            "description": description,
            "metadata": metadata or {},
            "receipt": {
                "customer": {"email": user_email},
                "items": [
                    {
                        "description": description,
                        "quantity": "1.00",
                        "amount": {"value": str(amount), "currency": "RUB"},
                        "vat_code": 1,
                        "payment_mode": "full_prepayment",
                        "payment_subject": "service",
                    }
                ],
            },
        }
        if save_payment_method:
            payment_data["save_payment_method"] = True

        payment = await asyncio.to_thread(
            Payment.create,
            payment_data,
            idempotency_key=idempotency_key or str(order_id),
        )

        logger.info("Payment created", order_id=order_id, payment_id=payment.id)
        return {
            "id": payment.id,
            "status": payment.status,
            "confirmation_url": payment.confirmation.confirmation_url,
        }

    async def charge_subscription_renewal(
        self,
        subscription_id: int,
        payment_method_id: str,
        amount: Decimal,
        description: str,
        user_email: str,
    ) -> Dict[str, Any]:
        """Рекуррентное списание по сохранённому payment_method_id (ЮKassa)."""
        payment_data: Dict[str, Any] = {
            "amount": {"value": str(amount), "currency": "RUB"},
            "payment_method_id": payment_method_id,
            "capture": True,
            "description": description,
            "metadata": {"subscription_id": str(subscription_id)},
            "receipt": {
                "customer": {"email": user_email},
                "items": [
                    {
                        "description": description,
                        "quantity": "1.00",
                        "amount": {"value": str(amount), "currency": "RUB"},
                        "vat_code": 1,
                        "payment_mode": "full_prepayment",
                        "payment_subject": "service",
                    }
                ],
            },
        }
        payment = await asyncio.to_thread(
            Payment.create,
            payment_data,
            idempotency_key=f"sub-renew-{subscription_id}-{datetime.now(timezone.utc).timestamp():.0f}",
        )
        logger.info(
            "Subscription renewal payment created",
            subscription_id=subscription_id,
            payment_id=payment.id,
        )
        return {"id": payment.id, "status": payment.status}

    async def get_payment(self, payment_id: str) -> Optional[Dict]:
        try:
            payment = await asyncio.to_thread(Payment.find_one, payment_id)
            return {
                "id": payment.id,
                "status": payment.status,
                "paid": payment.paid,
                "amount": payment.amount.value,
                "metadata": payment.metadata,
                "confirmation_url": getattr(getattr(payment, "confirmation", None), "confirmation_url", None),
            }
        except Exception as e:
            logger.error("Failed to fetch payment", payment_id=payment_id, error=str(e))
            return None

    async def verify_payment_notification_matches_api(
        self, event_type: str, payment_obj: dict
    ) -> bool:
        payment_id = payment_obj.get("id")
        if not payment_id:
            return False
        api = await self.get_payment(payment_id)
        if not api:
            return False
        st = api.get("status")
        paid = api.get("paid")
        if event_type == "payment.succeeded":
            return paid is True and st == "succeeded"
        if event_type == "payment.canceled":
            return st == "canceled"
        if event_type == "payment.waiting_for_capture":
            return st == "waiting_for_capture"
        logger.warning("Unknown payment webhook event for API check", event_type=event_type)
        return False

    async def process_webhook_event(self, event: Dict, db: AsyncSession) -> None:
        event_type = event.get("event")
        payment_obj = event.get("object")
        if not payment_obj:
            return

        payment_id = payment_obj["id"]
        metadata = payment_obj.get("metadata") or {}
        order_id = parse_order_id_from_metadata(metadata.get("order_id"))
        subscription_id = parse_subscription_id_from_metadata(metadata.get("subscription_id"))

        if order_id is None and subscription_id is not None:
            await self._handle_subscription_only_webhook(
                db, event_type, subscription_id, payment_obj, payment_id
            )
            return

        if order_id is None:
            logger.warning(
                "No valid order_id in payment metadata",
                payment_id=payment_id,
                metadata_keys=list(metadata.keys()),
            )
            return

        if event_type == "payment.succeeded":
            async with db.begin():
                stmt = (
                    update(Order)
                    .where(Order.id == order_id, Order.status == OrderStatus.PENDING)
                    .values(status=OrderStatus.PAID, yookassa_id=payment_id)
                    .returning(Order.id)
                )
                result = await db.execute(stmt)
                paid_order_id = result.scalar_one_or_none()
            if paid_order_id is not None:
                logger.info("Order marked as paid", order_id=paid_order_id)
                stmt = (
                    select(Order)
                    .where(Order.id == paid_order_id)
                    .options(joinedload(Order.tariff))
                )
                orow = await db.execute(stmt)
                order = orow.unique().scalar_one()
                pm_id = _payment_method_id_from_yookassa(payment_obj)
                if order.tariff.billing_type == "subscription" and pm_id:
                    await self._upsert_subscription_from_order(db, order, pm_id)
                from app.tasks.report_generation import generate_report_task

                generate_report_task.delay(paid_order_id)
            else:
                chk = await db.execute(select(Order.id).where(Order.id == order_id))
                if chk.scalar_one_or_none() is None:
                    logger.error("Order not found for payment", order_id=order_id)
                else:
                    logger.info(
                        "payment.succeeded ignored: order not in pending state",
                        order_id=order_id,
                    )

        elif event_type == "payment.canceled":
            async with db.begin():
                stmt = (
                    update(Order)
                    .where(Order.id == order_id, Order.status == OrderStatus.PENDING)
                    .values(status=OrderStatus.CANCELED)
                )
                result = await db.execute(stmt)
                if result.rowcount:
                    logger.info("Order canceled", order_id=order_id)

    async def _upsert_subscription_from_order(
        self, db: AsyncSession, order: Order, payment_method_id: str
    ) -> None:
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)
        async with db.begin():
            res = await db.execute(
                select(Subscription)
                .where(
                    Subscription.user_id == order.user_id,
                    Subscription.tariff_id == order.tariff_id,
                )
                .order_by(Subscription.id.desc())
                .limit(1)
            )
            existing = res.scalar_one_or_none()
            if existing:
                existing.yookassa_payment_method_id = payment_method_id
                existing.status = SubscriptionStatus.ACTIVE.value
                existing.current_period_start = now
                existing.current_period_end = period_end
                existing.updated_at = now
            else:
                new_sub = Subscription(
                    user_id=order.user_id,
                    tariff_id=order.tariff_id,
                    status=SubscriptionStatus.ACTIVE.value,
                    yookassa_payment_method_id=payment_method_id,
                    current_period_start=now,
                    current_period_end=period_end,
                    cancel_at_period_end=False,
                )
                db.add(new_sub)

    async def _handle_subscription_only_webhook(
        self,
        db: AsyncSession,
        event_type: str,
        subscription_id: int,
        payment_obj: dict,
        payment_id: str,
    ) -> None:
        """Продление подписки: в metadata только subscription_id."""
        if event_type != "payment.succeeded":
            return
        now = datetime.now(timezone.utc)
        async with db.begin():
            res = await db.execute(select(Subscription).where(Subscription.id == subscription_id))
            sub = res.scalar_one_or_none()
            if not sub:
                logger.error("Subscription not found for webhook", subscription_id=subscription_id)
                return
            base = sub.current_period_end or now
            if base < now:
                base = now
            new_end = base + timedelta(days=30)
            sub.current_period_start = base
            sub.current_period_end = new_end
            sub.status = SubscriptionStatus.ACTIVE.value
            sub.updated_at = now
            logger.info(
                "Subscription period extended",
                subscription_id=subscription_id,
                payment_id=payment_id,
                until=new_end.isoformat(),
            )

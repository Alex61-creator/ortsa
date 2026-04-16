import asyncio
from decimal import Decimal
from yookassa import Refund
import structlog
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.order import Order, OrderStatus
from app.models.report import Report, ReportStatus
from app.models.tariff import Tariff
from app.services.analytics import get_user_attribution, record_analytics_event

logger = structlog.get_logger(__name__)

class RefundService:
    async def verify_refund_notification_matches_api(
        self, event_type: str, refund_obj: dict[str, Any]
    ) -> bool:
        """Сверка возврата с объектом API (аналогично платежам)."""
        if event_type != "refund.succeeded":
            return True
        refund_id = refund_obj.get("id")
        if not refund_id:
            return False
        try:
            r = await asyncio.to_thread(Refund.find_one, refund_id)
        except Exception as e:
            logger.warning("Refund API verify failed", error=str(e))
            return False
        return getattr(r, "status", None) == "succeeded"

    async def create_refund(
        self,
        db: AsyncSession,
        order_id: int,
        amount: Decimal = None
    ) -> dict:
        stmt = select(Order).where(Order.id == order_id).with_for_update(skip_locked=True)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise ValueError("Order not found or locked")

        if order.status not in [OrderStatus.PAID, OrderStatus.COMPLETED]:
            raise ValueError(f"Order cannot be refunded. Current status: {order.status}")

        if not order.yookassa_id:
            raise ValueError("Order has no payment ID")

        refund_amount = amount if amount is not None else order.amount
        if refund_amount > order.amount - order.refunded_amount:
            raise ValueError("Refund amount exceeds remaining amount")

        refund_data = {
            "amount": {"value": str(refund_amount), "currency": "RUB"},
            "payment_id": order.yookassa_id,
            "description": f"Refund for order #{order.id}"
        }
        idempotency_key = f"refund_{order.id}_{refund_amount}"

        refund = await asyncio.to_thread(Refund.create, refund_data, idempotency_key)

        order.refund_id = refund.id
        order.refund_status = refund.status
        order.refunded_amount += refund_amount
        if refund.status == "succeeded":
            order.status = OrderStatus.REFUNDED
            stmt = select(Report).where(Report.order_id == order.id)
            report_result = await db.execute(stmt)
            report = report_result.scalar_one_or_none()
            if report:
                report.status = ReportStatus.ARCHIVED

        await db.commit()

        # Canonical event for event-based funnels/economics/audit.
        if refund.status == "succeeded":
            utm_source, utm_medium, utm_campaign, source_channel, platform, geo = await get_user_attribution(db, order.user_id)
            tariff_code = (
                (await db.execute(select(Tariff.code).where(Tariff.id == order.tariff_id))).scalar_one_or_none()
            )
            await record_analytics_event(
                db,
                event_name="refund_completed",
                user_id=order.user_id,
                order_id=order.id,
                tariff_code=tariff_code,
                source_channel=source_channel,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                platform=platform,
                geo=geo,
                amount=refund_amount,
                correlation_id=str(refund.id),
                dedupe_key=f"refund_completed:{refund.id}",
            )

        logger.info("Refund created", order_id=order.id, refund_id=refund.id, status=refund.status)

        if order.celery_task_id:
            from app.tasks.worker import celery_app
            celery_app.control.revoke(order.celery_task_id, terminate=True, signal="SIGTERM")

        return {"refund_id": refund.id, "status": refund.status, "amount": refund_amount}

    async def process_refund_webhook(self, event: dict, db: AsyncSession) -> None:
        refund_obj = event.get("object")
        if not refund_obj:
            return

        refund_id = refund_obj["id"]
        payment_id = refund_obj["payment_id"]
        status = refund_obj["status"]

        stmt = select(Order).where(
            (Order.yookassa_id == payment_id) | (Order.refund_id == refund_id)
        ).with_for_update(skip_locked=True)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            logger.warning("Order not found for refund webhook", refund_id=refund_id)
            return

        order.refund_status = status
        if status == "succeeded":
            order.status = OrderStatus.REFUNDED
            stmt = select(Report).where(Report.order_id == order.id)
            report_result = await db.execute(stmt)
            report = report_result.scalar_one_or_none()
            if report:
                report.status = ReportStatus.ARCHIVED

            if order.celery_task_id:
                from app.tasks.worker import celery_app
                celery_app.control.revoke(order.celery_task_id, terminate=True)

        await db.commit()

        if status == "succeeded":
            # Best-effort extraction for analytics amount.
            refund_amount_value = None
            amount_obj = refund_obj.get("amount")
            if isinstance(amount_obj, dict):
                raw_val = amount_obj.get("value") or amount_obj.get("amount")
                if raw_val is not None:
                    refund_amount_value = Decimal(str(raw_val))

            if refund_amount_value is None:
                refund_amount_value = order.refunded_amount or Decimal("0.00")

            utm_source, utm_medium, utm_campaign, source_channel, platform, geo = await get_user_attribution(db, order.user_id)
            tariff_code = (
                (await db.execute(select(Tariff.code).where(Tariff.id == order.tariff_id))).scalar_one_or_none()
            )
            await record_analytics_event(
                db,
                event_name="refund_completed",
                user_id=order.user_id,
                order_id=order.id,
                tariff_code=tariff_code,
                source_channel=source_channel,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                platform=platform,
                geo=geo,
                amount=refund_amount_value,
                correlation_id=str(refund_id),
                dedupe_key=f"refund_completed:{refund_id}",
            )

        logger.info("Refund webhook processed", order_id=order.id, refund_id=refund_id, status=status)
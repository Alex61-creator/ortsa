import json
from fastapi import APIRouter, Request, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.session import get_db
from app.services.payment import YookassaPaymentService
from app.services.refund import RefundService
from app.services.yookassa_webhook import (
    notification_idempotency_key,
    parse_notification,
)
from app.core.config import settings
from app.core.cache import cache
from app.utils.client_ip import get_client_ip
from app.utils.yookassa_ip import is_yookassa_notification_ip
from app.schemas.common import StatusOk

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post(
    "/yookassa",
    response_model=StatusOk,
    summary="Вебхук ЮKassa",
    description=(
        "HTTP-уведомления ЮKassa: платежи и возвраты. Проверка IP отправителя (опционально) "
        "и сверка объекта через API («Object status authentication»). Дубликаты отбрасываются "
        "по идемпотентному ключу в кэше."
    ),
)
async def yookassa_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StatusOk:
    body = await request.body()
    try:
        event = parse_notification(body)
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning("Invalid YooKassa notification body", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid body")

    event_type = event.get("event") or ""
    obj = event.get("object") or {}
    payment_id = obj.get("id") if event_type.startswith("payment.") else None
    refund_id = obj.get("id") if event_type.startswith("refund.") else None
    order_id = None
    metadata = obj.get("metadata") or {}
    raw_order_id = metadata.get("order_id")
    try:
        order_id = int(raw_order_id) if raw_order_id is not None else None
    except (TypeError, ValueError):
        order_id = None

    idem = notification_idempotency_key(event)
    # Атомарный SETNX: устанавливаем флаг ДО обработки, чтобы исключить race condition
    # при параллельных одинаковых webhook'ах. Если вернул False — дубликат, пропускаем.
    is_new = await cache.set_nx(idem, "processing", ttl=86400)
    if not is_new:
        logger.info(
            "dedupe_duplicate_ignored",
            idem=idem,
            event_type=event_type,
            payment_id=payment_id,
            refund_id=refund_id,
            order_id=order_id,
        )
        return StatusOk()
    logger.info(
        "dedupe_processing_set",
        idem=idem,
        event_type=event_type,
        payment_id=payment_id,
        refund_id=refund_id,
        order_id=order_id,
    )

    completed_successfully = False
    try:
        if settings.YOOKASSA_WEBHOOK_VERIFY_IP:
            client_ip = get_client_ip(request)
            if not is_yookassa_notification_ip(client_ip):
                logger.warning("YooKassa webhook rejected: IP not in allowlist", ip=client_ip)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid notification source",
                )

        if event_type.startswith("payment."):
            if settings.YOOKASSA_WEBHOOK_VERIFY_API:
                payment_service = YookassaPaymentService()
                if not await payment_service.verify_payment_notification_matches_api(
                    event_type, event.get("object") or {}
                ):
                    logger.warning(
                        "YooKassa payment webhook does not match API state",
                        event_type=event_type,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Notification does not match API",
                    )
            payment_service = YookassaPaymentService()
            await payment_service.process_webhook_event(event, db)

        elif event_type.startswith("refund."):
            if settings.YOOKASSA_WEBHOOK_VERIFY_API:
                refund_service = RefundService()
                if not await refund_service.verify_refund_notification_matches_api(
                    event_type, event.get("object") or {}
                ):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Notification does not match API",
                    )
            refund_service = RefundService()
            await refund_service.process_refund_webhook(event, db)
        else:
            logger.info("Unhandled YooKassa event", event_type=event_type)

        # Обновляем значение на "processed" после успешной обработки
        await cache.set(idem, "processed", ttl=86400)
        logger.info(
            "dedupe_processed",
            idem=idem,
            event_type=event_type,
            payment_id=payment_id,
            refund_id=refund_id,
            order_id=order_id,
        )
        completed_successfully = True
        return StatusOk()
    except Exception as exc:
        # Не оставляем ключ "processing" на весь TTL: короткий failed TTL позволяет повторить обработку.
        failed_ttl_seconds = 300
        try:
            await cache.set(idem, "failed", ttl=failed_ttl_seconds)
        except Exception:
            # Если кеш недоступен/упал, не скрываем первичную ошибку
            pass
        logger.exception(
            "dedupe_failed",
            idem=idem,
            event_type=event_type,
            payment_id=payment_id,
            refund_id=refund_id,
            order_id=order_id,
            error=str(exc),
        )
        raise
    finally:
        if completed_successfully:
            pass
        # Финальная страховка: при любом неуспешном выходе не оставляем "processing".
        else:
            try:
                current_state = await cache.get(idem)
                if current_state == "processing":
                    await cache.set(idem, "failed", ttl=300)
            except Exception:
                pass

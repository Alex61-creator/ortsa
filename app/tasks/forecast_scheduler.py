"""Планировщик ежемесячных forecast-отчётов для подписчиков.

Beat-задача запускается ежедневно и создаёт Order + ставит задачу генерации
для всех активных подписок, у которых пришло время нового forecast-окна.

Антидубли:
- before dispatch: проверяем orders по (user_id, tariff_code, forecast_window_start)
- idempotent: повторный запуск задачи за тот же день ничего не делает
"""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import structlog
from celery import shared_task
from sqlalchemy import select

from app.constants.forecast import DEFAULT_FORECAST_WINDOW_DAYS
from app.constants.tariffs import SUBSCRIPTION_CODES
from app.db.session import AsyncSessionLocal
from app.models.order import Order, OrderStatus
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.natal_data import NatalData
from app.models.tariff import Tariff

logger = structlog.get_logger(__name__)


@shared_task(
    name="app.tasks.forecast_scheduler.schedule_monthly_forecasts",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    default_retry_delay=300,
)
def schedule_monthly_forecasts(self):
    """Beat-задача: ставит forecast-генерацию для подписчиков, у кого подошло окно."""
    return asyncio.run(_schedule_monthly_forecasts_async())


async def _schedule_monthly_forecasts_async() -> dict:
    """Основная логика планировщика."""
    now = datetime.now(timezone.utc)
    scheduled = 0
    skipped = 0

    async with AsyncSessionLocal() as db:
        # Загружаем активные подписки subscription_codes
        subs_stmt = (
            select(Subscription)
            .join(Tariff, Tariff.id == Subscription.tariff_id)
            .where(
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Tariff.code.in_(SUBSCRIPTION_CODES),
            )
        )
        subs_result = await db.execute(subs_stmt)
        subscriptions = subs_result.scalars().all()

        logger.info("Forecast scheduler started", total_subs=len(subscriptions))

        for sub in subscriptions:
            try:
                result = await _maybe_schedule_forecast(db, sub, now)
                if result == "scheduled":
                    scheduled += 1
                else:
                    skipped += 1
            except Exception as exc:
                logger.error(
                    "Error scheduling forecast for subscription",
                    sub_id=sub.id,
                    user_id=sub.user_id,
                    error=str(exc),
                )
                skipped += 1

        await db.commit()

    logger.info(
        "Forecast scheduler done",
        scheduled=scheduled,
        skipped=skipped,
    )
    return {"scheduled": scheduled, "skipped": skipped}


async def _maybe_schedule_forecast(
    db,
    sub: Subscription,
    now: datetime,
) -> str:
    """
    Для одной подписки: проверяет нужен ли новый forecast и создаёт заказ.
    Возвращает 'scheduled' | 'skipped'.
    """
    # Определяем начало текущего окна (начало текущего месяца UTC)
    window_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    window_end = window_start + timedelta(days=DEFAULT_FORECAST_WINDOW_DAYS)

    # Проверяем: нет ли уже отчёта за это окно (антидубль)
    existing_stmt = select(Order).where(
        Order.user_id == sub.user_id,
        Order.tariff_id == sub.tariff_id,
        Order.forecast_window_start == window_start,
        Order.status.not_in([OrderStatus.CANCELED.value, OrderStatus.FAILED.value]),
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()
    if existing:
        logger.debug(
            "Forecast already exists for window",
            sub_id=sub.id,
            user_id=sub.user_id,
            window_start=window_start.isoformat(),
            existing_order_id=existing.id,
        )
        return "skipped"

    # Проверяем: пришло ли время нового forecast
    # (next_forecast_at не задан → сразу генерируем, иначе проверяем)
    if sub.next_forecast_at and sub.next_forecast_at > now:
        logger.debug(
            "Forecast not due yet",
            sub_id=sub.id,
            user_id=sub.user_id,
            next_forecast_at=sub.next_forecast_at.isoformat(),
        )
        return "skipped"

    # Ищем натальные данные пользователя (последние созданные)
    natal_stmt = (
        select(NatalData)
        .where(NatalData.user_id == sub.user_id)
        .order_by(NatalData.created_at.desc())
        .limit(1)
    )
    natal_result = await db.execute(natal_stmt)
    natal_data = natal_result.scalar_one_or_none()
    if not natal_data:
        logger.warning(
            "No natal data for subscriber, skipping",
            sub_id=sub.id,
            user_id=sub.user_id,
        )
        return "skipped"

    # Создаём Order с forecast-полями
    order = Order(
        user_id=sub.user_id,
        natal_data_id=natal_data.id,
        tariff_id=sub.tariff_id,
        status=OrderStatus.PAID,          # подписка уже оплачена — сразу PAID
        amount=Decimal("0.00"),            # стоимость 0 (покрыта подпиской)
        forecast_window_start=window_start,
        forecast_window_end=window_end,
    )
    db.add(order)
    await db.flush()  # получаем order.id

    # Обновляем scheduling-поля подписки
    sub.last_forecast_at = now
    sub.next_forecast_at = window_start + timedelta(days=DEFAULT_FORECAST_WINDOW_DAYS)

    await db.commit()

    # Ставим задачу генерации в очередь
    try:
        from app.tasks.report_generation import generate_report_task
        generate_report_task.delay(order.id)
        logger.info(
            "Forecast scheduled",
            sub_id=sub.id,
            user_id=sub.user_id,
            order_id=order.id,
            window_start=window_start.isoformat(),
            window_end=window_end.isoformat(),
        )
    except Exception as queue_exc:
        logger.error(
            "Failed to enqueue forecast generation",
            sub_id=sub.id,
            order_id=order.id,
            error=str(queue_exc),
        )

    return "scheduled"

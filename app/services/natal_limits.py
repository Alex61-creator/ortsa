"""Эффективный лимит сохранённых натальных карт по оплаченным заказам и подписке Pro."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.order import Order, OrderStatus
from app.models.subscription import Subscription, SubscriptionStatus
from app.utils.tariff_features import max_natal_profiles_from_tariff


async def get_effective_max_natal_profiles(db: AsyncSession, user_id: int) -> int:
    """
    Максимум из max_natal_profiles тарифов по:
    - заказам в статусе оплачено / в работе / завершён (не pending, не refunded/canceled);
    - активным подпискам.
    Если ничего не куплено — 1 профиль.
    """
    limit = 1

    order_stmt = (
        select(Order)
        .where(
            Order.user_id == user_id,
            Order.status.in_(
                [
                    OrderStatus.PAID,
                    OrderStatus.PROCESSING,
                    OrderStatus.COMPLETED,
                ]
            ),
        )
        .options(joinedload(Order.tariff))
    )
    order_result = await db.execute(order_stmt)
    for order in order_result.scalars().unique().all():
        if order.tariff:
            limit = max(limit, max_natal_profiles_from_tariff(order.tariff))

    sub_stmt = (
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE.value,
        )
        .options(joinedload(Subscription.tariff))
    )
    sub_result = await db.execute(sub_stmt)
    for sub in sub_result.scalars().unique().all():
        if sub.tariff:
            limit = max(limit, max_natal_profiles_from_tariff(sub.tariff))

    return limit

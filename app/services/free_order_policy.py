"""Ограничения на заказы с нулевой ценой (бесплатный тариф)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff


async def user_already_used_free_tariff(db: AsyncSession, user_id: int) -> bool:
    """Есть ли у пользователя уже заказ по тарифу free в конечном или оплаченном состоянии."""
    stmt = (
        select(Order.id)
        .join(Tariff, Order.tariff_id == Tariff.id)
        .where(
            Order.user_id == user_id,
            Tariff.code == "free",
            Order.status.in_(
                [
                    OrderStatus.PAID,
                    OrderStatus.PROCESSING,
                    OrderStatus.COMPLETED,
                ]
            ),
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus


async def compute_order_ops_metrics_dict(db: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(hours=2)

    failed_q = await db.execute(
        select(func.count()).select_from(Order).where(Order.status == OrderStatus.FAILED)
    )
    failed_orders_total = int(failed_q.scalar_one() or 0)

    stuck_q = await db.execute(
        select(func.count())
        .select_from(Order)
        .where(
            Order.status == OrderStatus.PROCESSING,
            Order.updated_at < threshold,
        )
    )
    processing_stuck_over_2h = int(stuck_q.scalar_one() or 0)

    return {
        "failed_orders_total": failed_orders_total,
        "processing_stuck_over_2h": processing_stuck_over_2h,
        "checked_at": now,
    }

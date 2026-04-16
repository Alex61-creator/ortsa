from datetime import datetime, timedelta, timezone
import math

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
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

    # paid->completed latency (seconds) from Redis samples
    paid_completed_latencies_key = "ops:paid_completed_latencies"
    lat_vals_raw = await cache.redis.lrange(paid_completed_latencies_key, 0, 999)
    latencies_seconds: list[float] = []
    for v in lat_vals_raw:
        try:
            latencies_seconds.append(float(v))
        except (TypeError, ValueError):
            continue
    latencies_seconds.sort()

    def _percentile(p: float) -> float | None:
        if not latencies_seconds:
            return None
        # nearest-rank percentile
        k = math.ceil((p / 100.0) * len(latencies_seconds))
        idx = max(k - 1, 0)
        return latencies_seconds[idx]

    paid_completed_latency_p50_seconds = _percentile(50.0)
    paid_completed_latency_p95_seconds = _percentile(95.0)

    return {
        "failed_orders_total": failed_orders_total,
        "processing_stuck_over_2h": processing_stuck_over_2h,
        "paid_completed_latency_p50_seconds": paid_completed_latency_p50_seconds,
        "paid_completed_latency_p95_seconds": paid_completed_latency_p95_seconds,
        "checked_at": now,
    }

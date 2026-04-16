from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feature_flag import FeatureFlag
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff


ADDONS_ENABLED_FLAG = "addons_enabled"


async def is_addons_enabled(db: AsyncSession) -> bool:
    row = (
        await db.execute(select(FeatureFlag).where(FeatureFlag.key == ADDONS_ENABLED_FLAG))
    ).scalar_one_or_none()
    return bool(row and row.enabled)


def _to_int(features: dict[str, Any], key: str, default: int) -> int:
    value = features.get(key)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


async def evaluate_addon_eligibility(
    db: AsyncSession,
    *,
    user_id: int,
    addon_tariff: Tariff,
) -> dict[str, Any]:
    features = addon_tariff.features if isinstance(addon_tariff.features, dict) else {}
    reasons: list[str] = []

    if not await is_addons_enabled(db):
        reasons.append("ADDONS_DISABLED")
        return {"eligible": False, "reasons": reasons, "parent_order_id": None, "offer_expires_at": None}

    required_codes = features.get("addon_requires_tariff_codes") or []
    if not isinstance(required_codes, list):
        required_codes = []
    if not required_codes:
        reasons.append("NO_PARENT_TARIFF_RULE")
        return {"eligible": False, "reasons": reasons, "parent_order_id": None, "offer_expires_at": None}

    parent_order_stmt = (
        select(Order)
        .join(Tariff, Tariff.id == Order.tariff_id)
        .where(
            Order.user_id == user_id,
            Order.status == OrderStatus.COMPLETED,
            Tariff.code.in_(required_codes),
        )
        .order_by(Order.created_at.desc())
        .limit(1)
    )
    parent_order = (await db.execute(parent_order_stmt)).scalar_one_or_none()
    if parent_order is None:
        reasons.append("PARENT_NOT_COMPLETED")
        return {"eligible": False, "reasons": reasons, "parent_order_id": None, "offer_expires_at": None}

    ttl_hours = _to_int(features, "addon_offer_ttl_hours", 72)
    offer_expires_at = parent_order.created_at + timedelta(hours=ttl_hours)
    if offer_expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        reasons.append("OFFER_EXPIRED")

    limit = _to_int(features, "addon_repeat_limit", 1)
    purchased_count_stmt = (
        select(func.count())
        .select_from(Order)
        .where(
            Order.user_id == user_id,
            Order.parent_order_id == parent_order.id,
            Order.tariff_id == addon_tariff.id,
            Order.status.in_(
                [
                    OrderStatus.PENDING,
                    OrderStatus.PAID,
                    OrderStatus.PROCESSING,
                    OrderStatus.COMPLETED,
                ]
            ),
        )
    )
    purchased_count = int((await db.scalar(purchased_count_stmt)) or 0)
    if purchased_count >= limit:
        reasons.append("ALREADY_PURCHASED")

    return {
        "eligible": len(reasons) == 0,
        "reasons": reasons,
        "parent_order_id": parent_order.id,
        "offer_expires_at": offer_expires_at,
    }

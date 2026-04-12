from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionStatus
from app.schemas.subscription import SubscriptionOut, subscription_status_message

router = APIRouter()


def _subscription_to_out(sub: Subscription) -> SubscriptionOut:
    return SubscriptionOut(
        id=sub.id,
        tariff_code=sub.tariff.code,
        tariff_name=sub.tariff.name,
        status=sub.status,
        amount=sub.tariff.price,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
        status_message=subscription_status_message(sub.status, sub.cancel_at_period_end),
    )


@router.get("/me", response_model=SubscriptionOut | None)
async def get_my_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = (
        select(Subscription)
        .where(
            Subscription.user_id == current_user.id,
            or_(
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Subscription.status == SubscriptionStatus.PAST_DUE.value,
            ),
        )
        .options(joinedload(Subscription.tariff))
        .order_by(Subscription.updated_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    sub = result.scalar_one_or_none()
    if not sub:
        return None
    return _subscription_to_out(sub)


@router.post("/me/cancel", response_model=SubscriptionOut)
async def cancel_my_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = (
        select(Subscription)
        .where(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE.value,
        )
        .options(joinedload(Subscription.tariff))
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription")
    sub.cancel_at_period_end = True
    sub.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(sub)
    return _subscription_to_out(sub)


@router.post("/me/resume", response_model=SubscriptionOut)
async def resume_my_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = (
        select(Subscription)
        .where(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE.value,
        )
        .options(joinedload(Subscription.tariff))
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription")
    if not sub.cancel_at_period_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription is not scheduled for cancellation",
        )
    sub.cancel_at_period_end = False
    sub.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(sub)
    return _subscription_to_out(sub)

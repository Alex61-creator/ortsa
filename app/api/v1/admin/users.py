import asyncio as aio
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.core.cache import cache
from app.db.session import get_db
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.models.user import User
from app.schemas.admin_user import AdminUserListItem, AdminUserOut

router = APIRouter()


@router.get("/", response_model=list[AdminUserListItem], summary="Пользователи (админ)")
async def list_users_admin(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Поиск по email"),
):
    stmt = select(User).order_by(User.created_at.desc())
    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(User.email.isnot(None)).where(User.email.ilike(term))
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    users = list(result.scalars().all())

    if not users:
        return []

    user_ids = [u.id for u in users]

    # Aggregate order stats per user
    stats_stmt = (
        select(
            Order.user_id,
            func.count(Order.id).label("orders_count"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Order.status.in_([OrderStatus.PAID, OrderStatus.COMPLETED]),
                            Order.amount,
                        ),
                        else_=Decimal("0"),
                    )
                ),
                Decimal("0"),
            ).label("total_spent"),
            func.max(Order.created_at).label("last_order_at"),
        )
        .where(Order.user_id.in_(user_ids))
        .group_by(Order.user_id)
    )
    stats_result = await db.execute(stats_stmt)
    stats_map = {row.user_id: row for row in stats_result.all()}

    # Latest paid/completed tariff per user via row_number window function
    rn_subq = (
        select(
            Order.user_id,
            Order.tariff_id,
            func.row_number()
            .over(partition_by=Order.user_id, order_by=Order.created_at.desc())
            .label("rn"),
        )
        .where(Order.user_id.in_(user_ids))
        .where(Order.status.in_([OrderStatus.PAID, OrderStatus.COMPLETED]))
        .subquery()
    )
    latest_result = await db.execute(
        select(rn_subq.c.user_id, rn_subq.c.tariff_id).where(rn_subq.c.rn == 1)
    )
    tariff_id_map: dict[int, int] = {row.user_id: row.tariff_id for row in latest_result.all()}

    tariff_map: dict[int, Tariff] = {}
    tariff_ids = list(set(tariff_id_map.values()))
    if tariff_ids:
        tariff_result = await db.execute(select(Tariff).where(Tariff.id.in_(tariff_ids)))
        tariff_map = {t.id: t for t in tariff_result.scalars().all()}

    # Check block status from Redis in parallel
    block_vals = await aio.gather(*[cache.get(f"admin:block:{uid}") for uid in user_ids])
    blocked_map: dict[int, bool] = {uid: bool(v) for uid, v in zip(user_ids, block_vals)}

    items: list[AdminUserListItem] = []
    for u in users:
        s = stats_map.get(u.id)
        tid = tariff_id_map.get(u.id)
        tariff = tariff_map.get(tid) if tid else None
        items.append(
            AdminUserListItem(
                id=u.id,
                email=u.email or "",
                oauth_provider=str(u.oauth_provider.value if u.oauth_provider else ""),
                is_admin=u.is_admin,
                created_at=u.created_at,
                consent_given_at=u.consent_given_at,
                total_spent=s.total_spent if s else Decimal("0.00"),
                orders_count=s.orders_count if s else 0,
                last_order_at=s.last_order_at if s else None,
                blocked=blocked_map.get(u.id, False),
                latest_tariff_name=tariff.name if tariff else None,
                latest_tariff_code=tariff.code if tariff else None,
            )
        )
    return items


@router.get("/{user_id}", response_model=AdminUserOut, summary="Пользователь по id (админ)")
async def get_user_admin(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.delete("/{user_id}", summary="Удалить пользователя (админ)")
async def delete_user_admin(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить свою учётную запись",
        )
    result = await db.execute(select(User).where(User.id == user_id))
    victim = result.scalar_one_or_none()
    if not victim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
    return {"deleted": True, "user_id": user_id}

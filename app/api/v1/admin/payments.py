from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.schemas.admin_extra import AdminPaymentRow

router = APIRouter()


@router.get("/", response_model=list[AdminPaymentRow], summary="Платежи (админ)")
async def list_payments(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Поиск по email или id заказа"),
    provider: Optional[str] = Query(None),
    tariff: Optional[str] = Query(None),
    payment_id: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
):
    stmt = (
        select(Order)
        .options(joinedload(Order.user), joinedload(Order.tariff))
        .order_by(Order.created_at.desc())
    )
    if status:
        try:
            stmt = stmt.where(Order.status == OrderStatus(status))
        except ValueError:
            pass
    if provider:
        stmt = stmt.where(Order.payment_provider == provider)
    if tariff:
        stmt = stmt.where(Order.tariff.has(code=tariff))
    if payment_id:
        stmt = stmt.where(and_(Order.yookassa_id.is_not(None), Order.yookassa_id.ilike(f"%{payment_id}%")))
    if email:
        stmt = stmt.where(Order.user.has(User.email.ilike(f"%{email}%")))
    if date_from:
        stmt = stmt.where(Order.created_at >= date_from)
    if date_to:
        stmt = stmt.where(Order.created_at <= date_to)
    if q and q.strip():
        term = q.strip().lower()
        if term.isdigit():
            stmt = stmt.where(Order.id == int(term))
    # Поиск по email делаем после joinedload на уровне Python для простоты и совместимости.
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).unique().scalars().all()
    if q and q.strip() and not q.strip().isdigit():
        low = q.strip().lower()
        rows = [r for r in rows if r.user.email and low in r.user.email.lower()]
    return [
        AdminPaymentRow(
            order_id=o.id,
            user_id=o.user_id,
            user_email=o.user.email,
            status=o.status.value,
            amount=o.amount,
            tariff_name=o.tariff.name,
            tariff_code=o.tariff.code,
            payment_provider=o.payment_provider,
            payment_id=o.yookassa_id,
            promo_code=o.promo_code,
            refunded_amount=o.refunded_amount,
            created_at=o.created_at,
        )
        for o in rows
    ]

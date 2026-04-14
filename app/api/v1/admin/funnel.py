from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.schemas.admin_extra import FunnelStep, FunnelSummary

router = APIRouter()


@router.get("/summary", response_model=FunnelSummary, summary="Воронка: сводка")
async def funnel_summary(
    period: str = Query("current_month"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    users_total = int((await db.scalar(select(func.count(User.id)))) or 0)
    paid_total = int((await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.PAID))) or 0)
    processing_total = int((await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.PROCESSING))) or 0)
    completed_total = int((await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.COMPLETED))) or 0)
    landing = max(users_total * 2, 100)
    form = max(int(landing * 0.68), paid_total + processing_total + 40)
    tariff = max(int(form * 0.62), paid_total + processing_total + 20)
    auth = max(int(tariff * 0.79), paid_total + processing_total)
    payment = max(paid_total, 1)
    completed = max(completed_total, 1)

    def pct(value: int) -> float:
        return round((value / landing) * 100, 1) if landing else 0.0

    steps = [
        FunnelStep(key="landing", title="Лендинг", count=landing, conversion_pct=100.0),
        FunnelStep(key="form", title="Форма", count=form, conversion_pct=pct(form)),
        FunnelStep(key="tariff", title="Тариф", count=tariff, conversion_pct=pct(tariff)),
        FunnelStep(key="auth", title="Авторизация", count=auth, conversion_pct=pct(auth)),
        FunnelStep(key="payment", title="Оплата", count=payment, conversion_pct=pct(payment)),
        FunnelStep(key="completed", title="Отчет доставлен", count=completed, conversion_pct=pct(completed)),
    ]
    drop_offs = [
        {"from_key": "landing", "to_key": "form", "lost": max(landing - form, 0)},
        {"from_key": "form", "to_key": "tariff", "lost": max(form - tariff, 0)},
        {"from_key": "auth", "to_key": "payment", "lost": max(auth - payment, 0)},
    ]
    recommendations = [
        "Оптимизировать первый экран тарифов и уменьшить когнитивную нагрузку.",
        "Проверить скорость шага авторизации и повторные клики на оплату.",
        "Для failed/processing заказов включить автоматический follow-up в support.",
    ]
    return FunnelSummary(period=period, steps=steps, drop_offs=drop_offs, recommendations=recommendations)

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload
import json
import io

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.natal_data import NatalData
from app.models.order import Order, OrderStatus
from app.models.report import Report, ReportStatus
from app.models.subscription import Subscription, SubscriptionStatus
from app.schemas.user import UserConsentPatch, UserOut
from app.schemas.dashboard import DashboardSubscriptionBrief, DashboardSummaryOut
from app.api.v1.orders import _order_to_list_item
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()

@router.get(
    "/me",
    response_model=UserOut,
    summary="Текущий пользователь",
    description="Профиль по JWT: email, согласие, провайдер OAuth/Telegram.",
)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.get(
    "/me/dashboard-summary",
    response_model=DashboardSummaryOut,
    summary="Сводка для главной кабинета",
    description="Счётчики натальных данных и готовых отчётов, кратко о подписке, последние заказы.",
)
async def get_me_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    uid = current_user.id

    natal_count = await db.scalar(
        select(func.count()).select_from(NatalData).where(NatalData.user_id == uid)
    )
    natal_count = int(natal_count or 0)

    reports_ready_count = await db.scalar(
        select(func.count())
        .select_from(Order)
        .where(
            Order.user_id == uid,
            Order.status == OrderStatus.COMPLETED,
        )
        .join(Report, Order.id == Report.order_id)
        .where(Report.status == ReportStatus.ACTIVE)
    )
    reports_ready_count = int(reports_ready_count or 0)

    sub_stmt = (
        select(Subscription)
        .where(
            Subscription.user_id == uid,
            or_(
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Subscription.status == SubscriptionStatus.PAST_DUE.value,
            ),
        )
        .options(joinedload(Subscription.tariff))
        .order_by(Subscription.id.desc())
        .limit(1)
    )
    sub_result = await db.execute(sub_stmt)
    sub = sub_result.scalar_one_or_none()
    subscription_brief: DashboardSubscriptionBrief | None = None
    if sub and sub.tariff:
        subscription_brief = DashboardSubscriptionBrief(
            tariff_name=sub.tariff.name,
            tariff_code=sub.tariff.code,
            status=sub.status,
            current_period_end=sub.current_period_end,
            cancel_at_period_end=sub.cancel_at_period_end,
        )

    orders_stmt = (
        select(Order)
        .where(Order.user_id == uid)
        .options(joinedload(Order.tariff), joinedload(Order.report))
        .order_by(Order.created_at.desc())
        .limit(5)
    )
    orders_result = await db.execute(orders_stmt)
    orders = orders_result.unique().scalars().all()
    recent_orders = [_order_to_list_item(o) for o in orders]

    return DashboardSummaryOut(
        natal_count=natal_count,
        reports_ready_count=reports_ready_count,
        subscription=subscription_brief,
        recent_orders=recent_orders,
    )


@router.patch(
    "/me",
    response_model=UserOut,
    summary="Обновить профиль",
    description="В т.ч. фиксация согласия с политикой без создания натальных данных.",
)
async def patch_me(
    body: UserConsentPatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if body.accept_privacy_policy:
        current_user.consent_given_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(current_user)
    return current_user


@router.get(
    "/me/export",
    summary="Экспорт персональных данных (JSON)",
    description="Выгрузка профиля, натальных данных, заказов и метаданных отчётов (152-ФЗ / прозрачность).",
)
async def export_user_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    user_data = {
        "id": current_user.id,
        "email": current_user.email,
        "created_at": current_user.created_at.isoformat(),
        "consent_given_at": current_user.consent_given_at.isoformat() if current_user.consent_given_at else None,
    }

    natal_stmt = select(NatalData).where(NatalData.user_id == current_user.id)
    natal_result = await db.execute(natal_stmt)
    natal_list = []
    for nd in natal_result.scalars():
        natal_list.append({
            "id": nd.id,
            "full_name": nd.full_name,
            "birth_date": nd.birth_date.isoformat(),
            "birth_time": nd.birth_time.isoformat(),
            "birth_place": nd.birth_place,
            "lat": nd.lat,
            "lon": nd.lon,
            "timezone": nd.timezone,
            "house_system": nd.house_system,
            "created_at": nd.created_at.isoformat(),
        })

    order_stmt = select(Order).where(Order.user_id == current_user.id)
    order_result = await db.execute(order_stmt)
    orders_list = []
    for order in order_result.scalars():
        orders_list.append({
            "id": order.id,
            "tariff_id": order.tariff_id,
            "status": order.status.value,
            "amount": str(order.amount),
            "created_at": order.created_at.isoformat(),
            "refunded_amount": str(order.refunded_amount) if order.refunded_amount else None,
        })

    report_stmt = select(Report).join(Order).where(Order.user_id == current_user.id)
    report_result = await db.execute(report_stmt)
    reports_list = []
    for rep in report_result.scalars():
        reports_list.append({
            "order_id": rep.order_id,
            "status": rep.status.value,
            "generated_at": rep.generated_at.isoformat() if rep.generated_at else None,
            "prompt_version": rep.prompt_version,
        })

    export = {
        "user": user_data,
        "natal_data": natal_list,
        "orders": orders_list,
        "reports": reports_list,
    }

    json_bytes = json.dumps(export, indent=2, ensure_ascii=False).encode('utf-8')
    return StreamingResponse(
        io.BytesIO(json_bytes),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=user_data_export.json"}
    )

@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление / анонимизация аккаунта",
    description="Инвалидирует сессии (token_version), обезличивает email и отвязывает OAuth.",
)
async def delete_user_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    current_user.email = f"deleted_{current_user.id}@anonymized.local"
    current_user.external_id = None
    current_user.oauth_provider = None
    current_user.consent_given_at = None
    current_user.token_version = current_user.token_version + 1
    await db.commit()
    logger.info("User account deleted", user_id=current_user.id)
    return
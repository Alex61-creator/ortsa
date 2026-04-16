from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.order import Order, OrderStatus
from app.models.tariff import Tariff
from app.models.user import User
from app.services.addons_access import evaluate_addon_eligibility, is_addons_enabled
from app.services.payment import YookassaPaymentService
from app.services.storage import StorageService
from app.constants.tariffs import ADDON_REPORT_TARIFF_CODES
from app.services.analytics import get_user_attribution, record_analytics_event

router = APIRouter()


class AddonOfferOut(BaseModel):
    addon_code: str
    title: str
    description: str | None = None
    price: str
    currency: str = "RUB"
    eligible: bool
    eligibility_reasons: list[str]
    parent_order_id: int | None = None
    offer_expires_at: datetime | None = None


class AddonPurchaseOut(BaseModel):
    payment_url: str
    addon_order_id: int
    status: str


class AddonOrderOut(BaseModel):
    order_id: int
    parent_order_id: int | None
    addon_code: str
    payment_status: str
    report_status: str
    progress: str
    artifacts: dict[str, Any]
    links: dict[str, str]
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=list[AddonOfferOut])
async def list_addons(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    addon_tariffs = (
        await db.execute(
            select(Tariff).where(
                Tariff.code.in_(list(ADDON_REPORT_TARIFF_CODES)),
            )
        )
    ).scalars().all()
    rows: list[AddonOfferOut] = []
    for tariff in addon_tariffs:
        eligibility = await evaluate_addon_eligibility(db, user_id=current_user.id, addon_tariff=tariff)
        if eligibility["eligible"]:
            utm_source, utm_medium, utm_campaign, source_channel, platform, geo = await get_user_attribution(db, current_user.id)
            await record_analytics_event(
                db,
                event_name="addon_offer_shown",
                user_id=current_user.id,
                tariff_code=tariff.code,
                source_channel=source_channel,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                platform=platform,
                geo=geo,
                dedupe_key=f"addon_offer_shown:{current_user.id}:{tariff.code}:{datetime.now().date().isoformat()}",
            )
        rows.append(
            AddonOfferOut(
                addon_code=tariff.code,
                title=tariff.name,
                price=str(tariff.price),
                eligible=bool(eligibility["eligible"]),
                eligibility_reasons=list(eligibility["reasons"]),
                parent_order_id=eligibility["parent_order_id"],
                offer_expires_at=eligibility["offer_expires_at"],
            )
        )
    return rows


@router.post("/{addon_slug}/purchase", response_model=AddonPurchaseOut)
async def purchase_addon(
    addon_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    tariff = (await db.execute(select(Tariff).where(Tariff.code == addon_slug))).scalar_one_or_none()
    if not tariff or addon_slug not in ADDON_REPORT_TARIFF_CODES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Addon not found")

    eligibility = await evaluate_addon_eligibility(db, user_id=current_user.id, addon_tariff=tariff)
    if not eligibility["eligible"]:
        utm_source, utm_medium, utm_campaign, source_channel, platform, geo = await get_user_attribution(db, current_user.id)
        await record_analytics_event(
            db,
            event_name="addon_purchase_blocked",
            user_id=current_user.id,
            tariff_code=tariff.code,
            source_channel=source_channel,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            platform=platform,
            geo=geo,
            event_metadata={"reasons": eligibility["reasons"]},
            dedupe_key=f"addon_purchase_blocked:{current_user.id}:{tariff.code}:{datetime.now().timestamp()}",
        )
        code = "ADDONS_DISABLED" if "ADDONS_DISABLED" in eligibility["reasons"] else "ADDON_NOT_ELIGIBLE"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": code,
                "message": "Add-on is not available",
                "details": {
                    "flag_key": "addons_enabled",
                    "reasons": eligibility["reasons"],
                },
            },
        )

    order = Order(
        user_id=current_user.id,
        tariff_id=tariff.id,
        amount=tariff.price,
        status=OrderStatus.PENDING,
        parent_order_id=eligibility["parent_order_id"],
        report_delivery_email=current_user.email,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    payment_service = YookassaPaymentService()
    payment = await payment_service.create_payment(
        order_id=order.id,
        amount=order.amount,
        description=f"Add-on purchase: {tariff.name}",
        user_email=current_user.email or "",
        metadata={"order_id": str(order.id), "tariff": tariff.code, "parent_order_id": str(order.parent_order_id)},
    )
    order.yookassa_id = payment["id"]
    await db.commit()

    utm_source, utm_medium, utm_campaign, source_channel, platform, geo = await get_user_attribution(db, current_user.id)
    await record_analytics_event(
        db,
        event_name="addon_purchase_started",
        user_id=current_user.id,
        order_id=order.id,
        tariff_code=tariff.code,
        source_channel=source_channel,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        platform=platform,
        geo=geo,
        amount=order.amount,
        dedupe_key=f"addon_purchase_started:{order.id}",
    )

    return AddonPurchaseOut(payment_url=payment["confirmation_url"], addon_order_id=order.id, status=order.status.value)


@router.get("/{order_id}", response_model=AddonOrderOut)
async def get_addon_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.user_id == current_user.id)
        .join(Tariff, Tariff.id == Order.tariff_id)
    )
    order = (await db.execute(stmt)).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Addon order not found")

    tariff = (await db.execute(select(Tariff).where(Tariff.id == order.tariff_id))).scalar_one()
    if tariff.code not in ADDON_REPORT_TARIFF_CODES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Addon order not found")

    report_status = "not_started"
    artifacts: dict[str, Any] = {}
    if order.report and order.report.pdf_path:
        storage = StorageService()
        resolved = storage.resolve_path(order.report.pdf_path)
        if resolved and resolved.exists():
            artifacts["pdf_path"] = order.report.pdf_path
        report_status = order.report.status.value if order.report else "not_started"
    progress = "queued"
    if order.status in (OrderStatus.PROCESSING,):
        progress = "generating"
    elif order.status == OrderStatus.COMPLETED:
        progress = "completed"
    elif order.status in (OrderStatus.FAILED, OrderStatus.CANCELED, OrderStatus.FAILED_TO_INIT_PAYMENT):
        progress = "failed"

    return AddonOrderOut(
        order_id=order.id,
        parent_order_id=order.parent_order_id,
        addon_code=tariff.code,
        payment_status=order.status.value,
        report_status=report_status,
        progress=progress,
        artifacts=artifacts,
        links={
            "dashboard_url": f"/dashboard/orders",
            "download_url": f"/reports/{order.id}",
            "support_url": "/dashboard/support",
        },
        created_at=order.created_at,
        updated_at=order.updated_at,
    )

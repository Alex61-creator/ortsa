from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.report import Report, ReportStatus
from app.models.order import Order, OrderStatus
from app.services.storage import StorageService

router = APIRouter()


class ReportStatusResponse(BaseModel):
    order_id: int
    order_status: str
    report_status: str | None
    report_type: str | None          # 'natal' | 'forecast' | 'synastry'
    report_ready: bool
    # Forecast-специфичные поля
    forecast_window_start: datetime | None
    forecast_window_end: datetime | None
    includes_transits: bool
    includes_progressions: bool
    generated_at: datetime | None


async def _get_user_completed_order_with_report(
    db: AsyncSession,
    order_id: int,
    user_id: int,
) -> Order | None:
    stmt = (
        select(Order)
        .join(Report, Report.order_id == Order.id)
        .where(
            Order.id == order_id,
            Order.user_id == user_id,
            Order.status == OrderStatus.COMPLETED,
            Report.status == ReportStatus.ACTIVE,
        )
        .options(joinedload(Order.report))
    )
    result = await db.execute(stmt)
    return result.unique().scalar_one_or_none()


@router.get(
    "/{order_id}/download",
    summary="Скачать PDF отчёта",
    description="Готовый PDF по завершённому заказу с активным отчётом. Только владелец заказа.",
    responses={
        200: {"content": {"application/pdf": {}}},
        404: {"description": "Отчёт не готов или заказ не найден"},
    },
)
async def download_report(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = await _get_user_completed_order_with_report(db, order_id, current_user.id)
    if not order or not order.report:
        raise HTTPException(status_code=404, detail="Report not found or not ready")

    storage = StorageService()
    pdf_path = storage.resolve_path(order.report.pdf_path)
    if not pdf_path:
        raise HTTPException(status_code=404, detail="Report file path is empty")
    if not pdf_path.exists():
        if order.report.status == ReportStatus.ARCHIVED:
            raise HTTPException(status_code=404, detail="Report expired and archived")
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"natal_report_{order_id}.pdf",
        headers={"Content-Disposition": f"attachment; filename=natal_report_{order_id}.pdf"},
    )


@router.get(
    "/{order_id}/chart",
    summary="Скачать PNG натальной карты",
    description="Изображение круга карт для завершённого заказа. Только владелец заказа.",
    responses={
        200: {"content": {"image/png": {}}},
        404: {"description": "Карта не найдена или заказ не готов"},
    },
)
async def download_chart(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = await _get_user_completed_order_with_report(db, order_id, current_user.id)
    if not order or not order.report:
        raise HTTPException(status_code=404, detail="Chart not found")

    storage = StorageService()
    chart_path = storage.resolve_path(order.report.chart_path)
    if not chart_path:
        raise HTTPException(status_code=404, detail="Chart path is empty")
    if not chart_path.exists():
        if order.report.status == ReportStatus.ARCHIVED:
            raise HTTPException(status_code=404, detail="Report expired and archived")
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(path=chart_path, media_type="image/png")


@router.get(
    "/{order_id}/status",
    response_model=ReportStatusResponse,
    summary="Статус отчёта",
    description=(
        "Возвращает статус заказа и отчёта, тип отчёта (natal/forecast/synastry) "
        "и forecast-окно для прогностических отчётов. Только владелец заказа."
    ),
)
async def get_report_status(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.user_id == current_user.id)
        .options(joinedload(Order.report), joinedload(Order.tariff))
    )
    result = await db.execute(stmt)
    order = result.unique().scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    report = order.report
    report_ready = bool(
        order.status == OrderStatus.COMPLETED
        and report
        and report.status == ReportStatus.ACTIVE
    )

    tariff_features: dict[str, Any] = {}
    if order.tariff and isinstance(order.tariff.features, dict):
        tariff_features = order.tariff.features

    return ReportStatusResponse(
        order_id=order.id,
        order_status=order.status.value,
        report_status=report.status.value if report else None,
        report_type=getattr(report, "report_type", "natal") if report else None,
        report_ready=report_ready,
        forecast_window_start=order.forecast_window_start,
        forecast_window_end=order.forecast_window_end,
        includes_transits=bool(tariff_features.get("includes_transits", False)),
        includes_progressions=bool(tariff_features.get("includes_progressions", False)),
        generated_at=report.generated_at if report else None,
    )

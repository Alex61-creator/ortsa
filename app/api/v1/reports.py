from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.report import Report, ReportStatus
from app.models.order import Order, OrderStatus
from app.core.config import settings

router = APIRouter()


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

    pdf_path = Path(settings.STORAGE_DIR) / order.report.pdf_path
    if not pdf_path.exists():
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

    chart_path = Path(settings.STORAGE_DIR) / order.report.chart_path
    if not chart_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(path=chart_path, media_type="image/png")

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_admin_user
from app.core.config import settings
from app.db.session import get_db
from app.models.order import Order
from app.models.report import Report
from app.models.user import User

router = APIRouter()


@router.get(
    "/orders/{order_id}/pdf",
    summary="Скачать PDF отчёта (админ)",
    responses={200: {"content": {"application/pdf": {}}}},
)
async def admin_download_report_pdf(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(joinedload(Order.report))
    )
    result = await db.execute(stmt)
    order = result.unique().scalar_one_or_none()
    if not order or not order.report or not order.report.pdf_path:
        raise HTTPException(status_code=404, detail="Report not found")
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
    "/orders/{order_id}/chart",
    summary="Скачать PNG карты (админ)",
    responses={200: {"content": {"image/png": {}}}},
)
async def admin_download_chart(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(joinedload(Order.report))
    )
    result = await db.execute(stmt)
    order = result.unique().scalar_one_or_none()
    if not order or not order.report or not order.report.chart_path:
        raise HTTPException(status_code=404, detail="Chart not found")
    chart_path = Path(settings.STORAGE_DIR) / order.report.chart_path
    if not chart_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")
    return FileResponse(path=chart_path, media_type="image/png")

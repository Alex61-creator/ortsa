from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.report import Report, ReportStatus
from app.models.order import Order, OrderStatus
from app.core.config import settings

router = APIRouter()

@router.get("/{order_id}/download")
async def download_report(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    stmt = select(Order).join(Report).where(
        Order.id == order_id,
        Order.user_id == current_user.id,
        Order.status == OrderStatus.COMPLETED,
        Report.status == ReportStatus.ACTIVE
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order or not order.report:
        raise HTTPException(status_code=404, detail="Report not found or not ready")

    pdf_path = Path(settings.STORAGE_DIR) / order.report.pdf_path
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"natal_report_{order_id}.pdf",
        headers={"Content-Disposition": f"attachment; filename=natal_report_{order_id}.pdf"}
    )

@router.get("/{order_id}/chart")
async def download_chart(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    stmt = select(Order).join(Report).where(
        Order.id == order_id,
        Order.user_id == current_user.id,
        Order.status == OrderStatus.COMPLETED,
        Report.status == ReportStatus.ACTIVE
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order or not order.report:
        raise HTTPException(status_code=404, detail="Chart not found")

    chart_path = Path(settings.STORAGE_DIR) / order.report.chart_path
    if not chart_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(path=chart_path, media_type="image/png")
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_admin_user
from app.api.v1.admin.logs import append_admin_log
from app.core.config import settings
from app.db.session import get_db
from app.models.order import Order
from app.models.report import Report, ReportStatus
from app.models.user import User
from app.services.email import EmailService

router = APIRouter()


class ResendEmailRequest(BaseModel):
    email_override: Optional[EmailStr] = None


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


@router.post(
    "/orders/{order_id}/resend-email",
    summary="Переотправить отчёт на email (админ)",
    description=(
        "Повторно отправляет готовый PDF-отчёт на email. "
        "Если указан email_override — отправляет на него; иначе на email из заказа или аккаунта пользователя."
    ),
)
async def admin_resend_report_email(
    order_id: int,
    body: ResendEmailRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_admin_user),
):
    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(joinedload(Order.report), joinedload(Order.user))
    )
    result = await db.execute(stmt)
    order = result.unique().scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not order.report or order.report.status != ReportStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Report not ready or not found")
    if not order.report.pdf_path:
        raise HTTPException(status_code=404, detail="PDF file not found in report record")

    pdf_path = Path(order.report.pdf_path)
    if not pdf_path.is_absolute():
        pdf_path = settings.STORAGE_DIR / order.report.pdf_path
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    # Приоритет: явный override → order.report_delivery_email → user.email
    to_addr = (
        str(body.email_override).strip()
        if body.email_override
        else (order.report_delivery_email or "").strip() or (
            order.user.email if order.user else None
        )
    )
    if not to_addr:
        raise HTTPException(status_code=400, detail="No delivery email available")

    email_service = EmailService()
    await email_service.send_email(
        recipients=[to_addr],
        subject=f"Натальная карта — Заказ #{order.id}",
        body="",
        template_name="report_ready.html",
        template_body={
            "user_name": order.user.email if order.user else "Пользователь",
            "order_id": order.id,
            "download_link": f"{settings.public_app_base_url}/reports/{order.id}",
        },
        attachments=[pdf_path],
    )

    await append_admin_log(
        actor.email or f"user:{actor.id}",
        "report_resend_email",
        f"order:{order_id}→{to_addr}",
    )

    return {"order_id": order_id, "sent_to": to_addr}

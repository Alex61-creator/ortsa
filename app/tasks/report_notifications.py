import asyncio

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import joinedload
import structlog

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.order import Order, OrderStatus
from app.models.report import ReportStatus
from app.services.analytics import get_user_attribution, record_analytics_event
from app.services.email import EmailService
from app.services.storage import StorageService

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=60)
def send_report_email_task(self, order_id: int):
    return asyncio.run(_send_report_email_async(order_id))


async def _send_report_email_async(order_id: int) -> None:
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(joinedload(Order.user), joinedload(Order.report), joinedload(Order.natal_data), joinedload(Order.tariff))
        )
        result = await db.execute(stmt)
        order = result.unique().scalar_one_or_none()
        if not order or not order.report:
            logger.warning("skip email: order/report missing", order_id=order_id)
            return
        if order.status != OrderStatus.COMPLETED or order.report.status != ReportStatus.ACTIVE:
            logger.warning("skip email: report not ready", order_id=order_id, order_status=str(order.status))
            return

        to_addr = (order.report_delivery_email or "").strip() or (order.user.email if order.user else None)
        if not to_addr:
            logger.warning("skip email: no recipient", order_id=order_id)
            return

        storage = StorageService()
        attachment = storage.resolve_path(order.report.pdf_path)
        if not attachment or not attachment.exists():
            logger.warning("skip email: pdf missing", order_id=order_id, pdf_path=order.report.pdf_path)
            return

        locale = "ru"
        if order.natal_data and getattr(order.natal_data, "report_locale", None) in ("ru", "en"):
            locale = order.natal_data.report_locale

        if locale == "en":
            mail_subject = f"Your natal chart is ready — Order #{order.id}"
            mail_template = "report_ready_en.html"
        else:
            mail_subject = f"Ваша натальная карта готова — Заказ #{order.id}"
            mail_template = "report_ready.html"

        email_service = EmailService()
        await email_service.send_email(
            recipients=[to_addr],
            subject=mail_subject,
            body="",
            template_name=mail_template,
            template_body={
                "user_name": order.natal_data.full_name if order.natal_data else "User",
                "order_id": order.id,
                "download_link": f"{settings.public_app_base_url}/reports/{order.id}",
            },
            attachments=[attachment],
        )

        utm_source, utm_medium, utm_campaign, source_channel, platform, geo = await get_user_attribution(
            db, order.user_id
        )
        await record_analytics_event(
            db,
            event_name="email_sent",
            user_id=order.user_id,
            order_id=order.id,
            tariff_code=order.tariff.code if order.tariff else None,
            source_channel=source_channel,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            platform=platform,
            geo=geo,
            dedupe_key=f"email_sent:{order.id}",
        )

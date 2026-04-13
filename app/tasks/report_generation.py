import asyncio
from datetime import datetime, timezone
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
import structlog

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.order import Order, OrderStatus
from app.models.report import Report, ReportStatus
from app.models.natal_data import NatalData
from app.models.tariff import Tariff
from app.services.astrology import AstrologyService
from app.services.llm import LLMService
from app.services.pdf import PDFGenerator
from app.services.email import EmailService
from app.services.storage import StorageService
from app.core.cache import cache
from app.constants.tariffs import LlmTier, resolve_llm_tier

logger = structlog.get_logger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=60)
def generate_report_task(self, order_id: int):
    return asyncio.run(_generate_report_async(order_id, self.request.id))

async def _generate_report_async(order_id: int, task_id: str):
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(joinedload(Order.user))
        )
        result = await db.execute(stmt)
        order = result.unique().scalar_one_or_none()
        if not order:
            logger.error("Order not found", order_id=order_id)
            return

        order.celery_task_id = task_id
        uid = order.user_id
        if order.status not in [OrderStatus.PAID, OrderStatus.PROCESSING]:
            logger.warning(
                "Order not in valid state",
                order_id=order_id,
                user_id=uid,
                status=order.status,
            )
            return

        order.status = OrderStatus.PROCESSING
        await db.commit()

        try:
            if order.natal_data_id:
                natal_stmt = select(NatalData).where(
                    NatalData.id == order.natal_data_id,
                    NatalData.user_id == order.user_id,
                )
            else:
                natal_stmt = (
                    select(NatalData)
                    .where(NatalData.user_id == order.user_id)
                    .order_by(NatalData.created_at.desc())
                )
            natal_result = await db.execute(natal_stmt)
            natal_data = natal_result.scalar_one_or_none()
            if not natal_data:
                raise ValueError("No natal data found")

            tariff_stmt = select(Tariff).where(Tariff.id == order.tariff_id)
            tariff_result = await db.execute(tariff_stmt)
            tariff = tariff_result.scalar_one()

            report_locale = (
                natal_data.report_locale
                if getattr(natal_data, "report_locale", None) in ("ru", "en")
                else "ru"
            )

            astro_service = AstrologyService()
            cache_key = astro_service.make_cache_key(
                name=natal_data.full_name,
                birth_date=natal_data.birth_date,
                birth_time=natal_data.birth_time,
                lat=natal_data.lat,
                lon=natal_data.lon,
                tz_str=natal_data.timezone,
                house_system=natal_data.house_system
            )
            chart_data = await cache.get(cache_key)
            if not chart_data:
                chart_result = await astro_service.calculate_chart(
                    name=natal_data.full_name,
                    birth_date=natal_data.birth_date,
                    birth_time=natal_data.birth_time,
                    lat=natal_data.lat,
                    lon=natal_data.lon,
                    tz_str=natal_data.timezone,
                    house_system=natal_data.house_system
                )
                chart_data = chart_result["instance"]
                await cache.set(cache_key, chart_data, ttl=30*24*3600)
                png_data = chart_result["png"]
            else:
                # re-calc for PNG if not cached
                chart_result = await astro_service.calculate_chart(
                    name=natal_data.full_name,
                    birth_date=natal_data.birth_date,
                    birth_time=natal_data.birth_time,
                    lat=natal_data.lat,
                    lon=natal_data.lon,
                    tz_str=natal_data.timezone,
                    house_system=natal_data.house_system
                )
                png_data = chart_result["png"]

            storage = StorageService()
            chart_filename = f"charts/{order_id}_{datetime.utcnow().timestamp()}.png"
            chart_path = await storage.save_file(png_data, chart_filename)

            llm_service = LLMService()
            interpretation = await llm_service.generate_interpretation(
                chart_data, tariff, locale=report_locale
            )

            pdf_generator = PDFGenerator()
            tier = resolve_llm_tier(tariff.code, getattr(tariff, "llm_tier", None))
            pdf_template = "report_free.html" if tier == LlmTier.FREE else "report.html"
            context = {
                "locale": report_locale,
                "full_name": natal_data.full_name,
                "birth_data": f"{natal_data.birth_date.strftime('%d.%m.%Y')} {natal_data.birth_time.strftime('%H:%M')}",
                "birth_place": natal_data.birth_place,
                "chart_img_path": f"/app/storage/{chart_filename}",
                "interpretation": interpretation.raw_content,
                "tariff_name": tariff.name,
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            }
            pdf_filename = f"reports/report_{order_id}.pdf"
            pdf_path = await pdf_generator.generate(pdf_template, context, pdf_filename)

            report_stmt = select(Report).where(Report.order_id == order.id)
            report_result = await db.execute(report_stmt)
            report = report_result.scalar_one_or_none()
            if not report:
                report = Report(order_id=order.id)
                db.add(report)
            report.pdf_path = str(pdf_path)
            report.chart_path = str(chart_path)
            report.status = ReportStatus.ACTIVE
            report.generated_at = datetime.now(timezone.utc)

            order.status = OrderStatus.COMPLETED
            await db.commit()

            email_service = EmailService()
            if report_locale == "en":
                mail_subject = f"Your natal chart is ready — Order #{order.id}"
                mail_template = "report_ready_en.html"
            else:
                mail_subject = f"Ваша натальная карта готова — Заказ #{order.id}"
                mail_template = "report_ready.html"
            to_addr = (order.report_delivery_email or "").strip() or (
                order.user.email if order.user else None
            )
            if not to_addr:
                raise ValueError("No delivery email for report")

            await email_service.send_email(
                recipients=[to_addr],
                subject=mail_subject,
                body="",
                template_name=mail_template,
                template_body={
                    "user_name": natal_data.full_name,
                    "order_id": order.id,
                    # Канонический путь SPA: /reports/:orderId (см. frontend/src/routes/AppRoutes.tsx)
                    "download_link": f"{settings.public_app_base_url}/reports/{order.id}",
                },
                attachments=[pdf_path],
            )

            logger.info(
                "Report generation completed",
                order_id=order.id,
                user_id=order.user_id,
            )

        except Exception as e:
            logger.exception(
                "Report generation failed",
                order_id=order.id,
                user_id=order.user_id,
                error=str(e),
            )
            order.status = OrderStatus.FAILED
            report_stmt = select(Report).where(Report.order_id == order.id)
            report_result = await db.execute(report_stmt)
            report = report_result.scalar_one_or_none()
            if not report:
                report = Report(order_id=order.id)
                db.add(report)
            report.status = ReportStatus.FAILED
            await db.commit()
            raise
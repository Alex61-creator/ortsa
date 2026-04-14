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
from app.models.prompt_template import LlmPromptTemplate
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
            tariff_stmt = select(Tariff).where(Tariff.id == order.tariff_id)
            tariff_result = await db.execute(tariff_stmt)
            tariff = tariff_result.scalar_one()

            tier = resolve_llm_tier(tariff.code, getattr(tariff, "llm_tier", None))

            # Загружаем список натальных профилей для этого заказа.
            # Для bundle: primary + дополнительные из order_natal_items.
            # Для остальных: только primary.
            natal_profiles: list[NatalData] = []

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
            primary_natal = natal_result.scalar_one_or_none()
            if not primary_natal:
                raise ValueError("No natal data found")
            natal_profiles.append(primary_natal)

            # Дополнительные профили для bundle (slot_index >= 2)
            if tariff.code == "bundle":
                from app.models.order_natal_item import OrderNatalItem
                extras_stmt = (
                    select(OrderNatalItem)
                    .where(OrderNatalItem.order_id == order.id)
                    .order_by(OrderNatalItem.slot_index)
                )
                extras_result = await db.execute(extras_stmt)
                for item in extras_result.scalars().all():
                    nd_stmt = select(NatalData).where(NatalData.id == item.natal_data_id)
                    nd_res = await db.execute(nd_stmt)
                    nd = nd_res.scalar_one_or_none()
                    if nd and nd.id != primary_natal.id:
                        natal_profiles.append(nd)

            # Загружаем системный промпт из БД (если задан)
            report_locale = (
                primary_natal.report_locale
                if getattr(primary_natal, "report_locale", None) in ("ru", "en")
                else "ru"
            )
            prompt_stmt = select(LlmPromptTemplate).where(
                LlmPromptTemplate.tariff_code == tariff.code,
                LlmPromptTemplate.locale == report_locale,
            )
            prompt_result = await db.execute(prompt_stmt)
            prompt_rec = prompt_result.scalar_one_or_none()
            system_prompt_override = prompt_rec.system_prompt if prompt_rec else None

            astro_service = AstrologyService()
            llm_service = LLMService()
            pdf_generator = PDFGenerator()
            storage = StorageService()
            pdf_template = "report_free.html" if tier == LlmTier.FREE else "report.html"

            generated_pdf_paths = []

            for slot_idx, natal_data in enumerate(natal_profiles):
                nd_locale = (
                    natal_data.report_locale
                    if getattr(natal_data, "report_locale", None) in ("ru", "en")
                    else "ru"
                )
                cache_key = astro_service.make_cache_key(
                    name=natal_data.full_name,
                    birth_date=natal_data.birth_date,
                    birth_time=natal_data.birth_time,
                    lat=natal_data.lat,
                    lon=natal_data.lon,
                    tz_str=natal_data.timezone,
                    house_system=natal_data.house_system,
                )
                chart_data = await cache.get(cache_key)
                chart_result = await astro_service.calculate_chart(
                    name=natal_data.full_name,
                    birth_date=natal_data.birth_date,
                    birth_time=natal_data.birth_time,
                    lat=natal_data.lat,
                    lon=natal_data.lon,
                    tz_str=natal_data.timezone,
                    house_system=natal_data.house_system,
                )
                if not chart_data:
                    chart_data = chart_result["instance"]
                    await cache.set(cache_key, chart_data, ttl=30 * 24 * 3600)
                png_data = chart_result["png"]

                chart_filename = f"charts/{order_id}_slot{slot_idx}_{datetime.utcnow().timestamp()}.png"
                chart_path = await storage.save_file(png_data, chart_filename)

                # Для bundle: промпт может зависеть от локали каждого профиля
                sp_override = system_prompt_override
                if nd_locale != report_locale:
                    p_stmt = select(LlmPromptTemplate).where(
                        LlmPromptTemplate.tariff_code == tariff.code,
                        LlmPromptTemplate.locale == nd_locale,
                    )
                    p_res = await db.execute(p_stmt)
                    p_rec = p_res.scalar_one_or_none()
                    sp_override = p_rec.system_prompt if p_rec else None

                interpretation = await llm_service.generate_interpretation(
                    chart_data, tariff, locale=nd_locale,
                    system_prompt_override=sp_override,
                )

                context = {
                    "locale": nd_locale,
                    "full_name": natal_data.full_name,
                    "birth_data": f"{natal_data.birth_date.strftime('%d.%m.%Y')} {natal_data.birth_time.strftime('%H:%M')}",
                    "birth_place": natal_data.birth_place,
                    "chart_img_path": f"/app/storage/{chart_filename}",
                    "interpretation": interpretation.raw_content,
                    "tariff_name": tariff.name,
                    "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                }
                suffix = f"_slot{slot_idx}" if slot_idx > 0 else ""
                pdf_filename = f"reports/report_{order_id}{suffix}.pdf"
                pdf_path = await pdf_generator.generate(pdf_template, context, pdf_filename)
                generated_pdf_paths.append(pdf_path)

            # Сохраняем Report (первый PDF как основной)
            report_stmt = select(Report).where(Report.order_id == order.id)
            report_result = await db.execute(report_stmt)
            report = report_result.scalar_one_or_none()
            if not report:
                report = Report(order_id=order.id)
                db.add(report)
            report.pdf_path = str(generated_pdf_paths[0])
            report.chart_path = str(chart_path)  # chart последнего (или единственного) слота
            report.status = ReportStatus.ACTIVE
            report.generated_at = datetime.now(timezone.utc)

            order.status = OrderStatus.COMPLETED
            await db.commit()

            email_service = EmailService()
            to_addr = (order.report_delivery_email or "").strip() or (
                order.user.email if order.user else None
            )
            if not to_addr:
                raise ValueError("No delivery email for report")

            # Отправляем письмо с первым PDF + extras как вложения (bundle)
            primary_locale = (
                primary_natal.report_locale
                if getattr(primary_natal, "report_locale", None) in ("ru", "en")
                else "ru"
            )
            if primary_locale == "en":
                mail_subject = f"Your natal chart is ready — Order #{order.id}"
                mail_template = "report_ready_en.html"
            else:
                mail_subject = f"Ваша натальная карта готова — Заказ #{order.id}"
                mail_template = "report_ready.html"

            await email_service.send_email(
                recipients=[to_addr],
                subject=mail_subject,
                body="",
                template_name=mail_template,
                template_body={
                    "user_name": primary_natal.full_name,
                    "order_id": order.id,
                    "download_link": f"{settings.public_app_base_url}/reports/{order.id}",
                },
                attachments=generated_pdf_paths,  # все PDF для bundle
            )

            logger.info(
                "Report generation completed",
                order_id=order.id,
                user_id=order.user_id,
                profiles=len(natal_profiles),
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
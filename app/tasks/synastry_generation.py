"""Celery-задача асинхронной генерации PDF-отчёта синастрии."""

import asyncio
from datetime import datetime, timezone, timedelta

import structlog
from celery import shared_task
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.natal_data import NatalData
from app.models.synastry_report import SynastryReport, SynastryStatus
from app.services.astrology import AstrologyService
from app.services.email import EmailService
from app.services.pdf import PDFGenerator
from app.services.storage import StorageService
from app.services.synastry_access import compute_input_hash
from app.services.synastry_llm import SynastryLLMService
from app.core.config import settings
from app.schemas.astrology import SynastryResultSchema

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=60)
def generate_synastry_task(self, synastry_id: int, tariff_code: str):
    return asyncio.run(_generate_synastry_async(synastry_id, tariff_code, self.request.id))


async def _generate_synastry_async(synastry_id: int, tariff_code: str, task_id: str):
    async with AsyncSessionLocal() as db:
        stmt = select(SynastryReport).where(SynastryReport.id == synastry_id)
        result = await db.execute(stmt)
        report = result.scalar_one_or_none()
        if not report:
            logger.error("SynastryReport not found", synastry_id=synastry_id)
            return

        report.celery_task_id = task_id
        report.status = SynastryStatus.PROCESSING
        await db.commit()

        try:
            # Загружаем обоих пользователей
            nd1_stmt = select(NatalData).where(NatalData.id == report.natal_data_id_1)
            nd2_stmt = select(NatalData).where(NatalData.id == report.natal_data_id_2)
            nd1 = (await db.execute(nd1_stmt)).scalar_one()
            nd2 = (await db.execute(nd2_stmt)).scalar_one()

            locale = report.locale

            # Проверяем hash — если не изменился, не регенерируем
            current_hash = compute_input_hash(nd1, nd2)
            if report.input_hash == current_hash and report.pdf_path:
                logger.info(
                    "Synastry data unchanged, skipping LLM call",
                    synastry_id=synastry_id,
                )
                report.status = SynastryStatus.COMPLETED
                await db.commit()
                return

            # ── Расчёт синастрии ──────────────────────────────────────────
            astro = AstrologyService()
            chart_result = await astro.calculate_synastry(
                person1={
                    "name": nd1.full_name,
                    "birth_date": nd1.birth_date,
                    "birth_time": nd1.birth_time,
                    "lat": nd1.lat,
                    "lon": nd1.lon,
                    "tz_str": nd1.timezone,
                    "house_system": nd1.house_system,
                },
                person2={
                    "name": nd2.full_name,
                    "birth_date": nd2.birth_date,
                    "birth_time": nd2.birth_time,
                    "lat": nd2.lat,
                    "lon": nd2.lon,
                    "tz_str": nd2.timezone,
                    "house_system": nd2.house_system,
                },
            )
            chart_result_valid = SynastryResultSchema.model_validate(chart_result)

            png_data = chart_result_valid.png

            # ── Сохранение PNG колеса ─────────────────────────────────────
            storage = StorageService()
            chart_filename = f"charts/synastry_{synastry_id}_{datetime.utcnow().timestamp():.0f}.png"
            chart_path = await storage.save_file(png_data, chart_filename)

            # ── LLM интерпретация ─────────────────────────────────────────
            llm_data = {
                "subject1": chart_result_valid.subject1.model_dump(mode="json"),
                "subject2": chart_result_valid.subject2.model_dump(mode="json"),
                "aspects": chart_result_valid.aspects,
            }
            llm_service = SynastryLLMService()
            interpretation, llm_provider_used = await llm_service.generate_synastry_interpretation(
                person1_name=nd1.full_name,
                person2_name=nd2.full_name,
                chart_data=llm_data,
                locale=locale,
                chart_context=(
                    chart_result_valid.llm_context if settings.LLM_USE_KERYKEION_CONTEXT else None
                ),
                user_id=report.user_id,
                synastry_id=synastry_id,
            )

            # ── Генерация PDF ─────────────────────────────────────────────
            pdf_generator = PDFGenerator()
            context = {
                "locale": locale,
                "person1_name": nd1.full_name,
                "person2_name": nd2.full_name,
                "person1_birth_data": (
                    f"{nd1.birth_date.strftime('%d.%m.%Y')} "
                    f"{nd1.birth_time.strftime('%H:%M')}"
                ),
                "person2_birth_data": (
                    f"{nd2.birth_date.strftime('%d.%m.%Y')} "
                    f"{nd2.birth_time.strftime('%H:%M')}"
                ),
                "person1_birth_place": nd1.birth_place,
                "person2_birth_place": nd2.birth_place,
                "chart_img_path": str(chart_path),
                "chart_data": chart_result_valid.model_dump(mode="json"),
                "interpretation": interpretation.raw_content,
                "interpretation_sections": interpretation.sections,
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            }
            pdf_filename = f"reports/synastry_{synastry_id}.pdf"
            pdf_path = await pdf_generator.generate("synastry.html", context, pdf_filename)

            # ── Обновляем запись ──────────────────────────────────────────
            report.pdf_path = storage.to_storage_key(pdf_path)
            report.chart_path = storage.to_storage_key(chart_path)
            report.status = SynastryStatus.COMPLETED
            report.input_hash = current_hash
            report.generation_count = (report.generation_count or 0) + 1
            report.last_generated_at = datetime.now(timezone.utc)
            report.llm_provider = llm_provider_used.value
            if report.retention_days and not report.expires_at:
                report.expires_at = datetime.now(timezone.utc) + timedelta(days=report.retention_days)
            await db.commit()

            logger.info(
                "Synastry report generated",
                synastry_id=synastry_id,
                generation_count=report.generation_count,
            )

            # ── Email уведомление ─────────────────────────────────────────
            try:
                user_stmt = select(NatalData).where(NatalData.id == report.natal_data_id_1)
                # email берём из User через natal_data.user
                from app.models.user import User
                user_stmt2 = (
                    select(User)
                    .where(User.id == report.user_id)
                )
                user = (await db.execute(user_stmt2)).scalar_one_or_none()
                if user and user.email:
                    email_service = EmailService()
                    subject = (
                        "Your synastry report is ready"
                        if locale == "en"
                        else f"Отчёт синастрии готов: {nd1.full_name} & {nd2.full_name}"
                    )
                    await email_service.send_email(
                        recipients=[user.email],
                        subject=subject,
                        body="",
                        template_name="synastry_ready.html",
                        template_body={
                            "person1_name": nd1.full_name,
                            "person2_name": nd2.full_name,
                            "download_link": (
                                f"{settings.public_app_base_url}"
                                f"/dashboard/synastry/{synastry_id}"
                            ),
                        },
                        attachments=[pdf_path],
                    )
            except Exception as email_err:
                # Ошибка email не должна откатывать успешную генерацию
                logger.warning(
                    "Synastry email notification failed",
                    synastry_id=synastry_id,
                    error=str(email_err),
                )

        except Exception as exc:
            logger.exception(
                "Synastry generation failed",
                synastry_id=synastry_id,
                error=str(exc),
            )
            report.status = SynastryStatus.FAILED
            await db.commit()
            raise

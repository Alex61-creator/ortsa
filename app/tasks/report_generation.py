import asyncio
from datetime import datetime, timezone
from celery import shared_task
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
from app.services.storage import StorageService
from app.services.email import EmailService  # backward-compatible import for tests
from app.services.prompt_templates import PromptTemplateService
from app.core.cache import cache
from app.constants.tariffs import LlmTier, resolve_llm_tier
from app.schemas.astrology import ChartResultSchema
from app.services.analytics import get_user_attribution, record_analytics_event
from app.constants.tariffs import ADDON_REPORT_TARIFF_CODES

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
        utm_source, utm_medium, utm_campaign, source_channel, platform, geo = await get_user_attribution(db, order.user_id)
        await record_analytics_event(
            db,
            event_name="report_generation_started",
            user_id=order.user_id,
            order_id=order.id,
            tariff_code=None,
            source_channel=source_channel,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            platform=platform,
            geo=geo,
            dedupe_key=f"report_generation_started:{order.id}",
        )
        try:
            failed_step = "init"
            tariff_stmt = select(Tariff).where(Tariff.id == order.tariff_id)
            tariff_result = await db.execute(tariff_stmt)
            tariff = tariff_result.scalar_one()
            if tariff.code in ADDON_REPORT_TARIFF_CODES:
                await record_analytics_event(
                    db,
                    event_name="addon_report_generation_started",
                    user_id=order.user_id,
                    order_id=order.id,
                    tariff_code=tariff.code,
                    source_channel=source_channel,
                    utm_source=utm_source,
                    utm_medium=utm_medium,
                    utm_campaign=utm_campaign,
                    platform=platform,
                    geo=geo,
                    dedupe_key=f"addon_report_generation_started:{order.id}",
                )

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
                extras = extras_result.scalars().all()
                extra_ids = [item.natal_data_id for item in extras]
                if extra_ids:
                    nd_stmt = select(NatalData).where(NatalData.id.in_(extra_ids))
                    nd_res = await db.execute(nd_stmt)
                    nd_by_id = {nd.id: nd for nd in nd_res.scalars().all()}
                    for item in extras:
                        nd = nd_by_id.get(item.natal_data_id)
                        if nd and nd.id != primary_natal.id:
                            natal_profiles.append(nd)

            # Загружаем системный промпт из БД (если задан)
            report_locale = (
                primary_natal.report_locale
                if getattr(primary_natal, "report_locale", None) in ("ru", "en")
                else "ru"
            )
            if report_locale not in ("ru", "en"):
                report_locale = "ru"
            system_prompt_override = await PromptTemplateService.get_system_prompt(
                db, tariff.code, report_locale
            )

            astro_service = AstrologyService()
            llm_service = LLMService()
            pdf_generator = PDFGenerator()
            storage = StorageService()
            pdf_template = "report_free.html" if tier == LlmTier.FREE else "report.html"

            generated_pdf_paths = []
            chart_paths = []

            if not natal_profiles:
                raise ValueError("No natal profiles for order")

            for slot_idx, natal_data in enumerate(natal_profiles):
                nd_locale = natal_data.report_locale if getattr(natal_data, "report_locale", None) in ("ru", "en") else "ru"
                if nd_locale not in ("ru", "en"):
                    nd_locale = "ru"

                failed_step = f"chart (slot {slot_idx})"
                cache_key = astro_service.make_cache_key(
                    name=natal_data.full_name,
                    birth_date=natal_data.birth_date,
                    birth_time=natal_data.birth_time,
                    lat=natal_data.lat,
                    lon=natal_data.lon,
                    tz_str=natal_data.timezone,
                    house_system=natal_data.house_system,
                )

                chart_cached_instance = await cache.get(cache_key)
                chart_result = await astro_service.calculate_chart(
                    name=natal_data.full_name,
                    birth_date=natal_data.birth_date,
                    birth_time=natal_data.birth_time,
                    lat=natal_data.lat,
                    lon=natal_data.lon,
                    tz_str=natal_data.timezone,
                    house_system=natal_data.house_system,
                )
                chart_result_valid = ChartResultSchema.model_validate(chart_result)

                png_data = chart_result_valid.png
                chart_data = chart_cached_instance or chart_result_valid.instance.model_dump(mode="json")
                if not chart_cached_instance:
                    await cache.set(cache_key, chart_data, ttl=30 * 24 * 3600)

                chart_filename = f"charts/{order_id}_slot{slot_idx}_{datetime.utcnow().timestamp()}.png"
                chart_path = await storage.save_file(png_data, chart_filename)

                failed_step = f"llm interpretation (slot {slot_idx})"
                # Для bundle: промпт может зависеть от локали каждого профиля
                sp_override = system_prompt_override
                if nd_locale != report_locale:
                    sp_override = await PromptTemplateService.get_system_prompt(
                        db, tariff.code, nd_locale
                    )

                interpretation = await llm_service.generate_interpretation(
                    chart_data=chart_data,
                    tariff=tariff,
                    locale=nd_locale,
                    system_prompt_override=sp_override,
                    chart_context=(
                        chart_result_valid.llm_context if settings.LLM_USE_KERYKEION_CONTEXT else None
                    ),
                )

                failed_step = f"pdf generation (slot {slot_idx})"
                context = {
                    "locale": nd_locale,
                    "full_name": natal_data.full_name,
                    "birth_data": f"{natal_data.birth_date.strftime('%d.%m.%Y')} {natal_data.birth_time.strftime('%H:%M')}",
                    "birth_place": natal_data.birth_place,
                    "chart_img_path": str(chart_path),
                    "interpretation": interpretation.raw_content,
                    "interpretation_sections": interpretation.sections,
                    "chart_data": chart_data,
                    "tariff_name": tariff.name,
                    "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                }

                # Canonical: first PDF goes to `report.pdf_path`
                pdf_filename = (
                    f"reports/report_{order_id}.pdf"
                    if slot_idx == 0
                    else f"reports/report_{order_id}_slot{slot_idx}.pdf"
                )
                pdf_path = await pdf_generator.generate(pdf_template, context, pdf_filename)
                if not pdf_path:
                    raise ValueError(f"PDF generation returned empty (slot {slot_idx})")

                generated_pdf_paths.append(pdf_path)
                chart_paths.append(chart_path)

            # ── Guard-checks before completing order ─────────────────────────
            failed_step = "persist report/order"
            if not generated_pdf_paths or not generated_pdf_paths[0]:
                raise ValueError("No generated PDFs")
            if not chart_paths or not chart_paths[0]:
                raise ValueError("No generated chart paths")

            # Observability: paid->completed latency (фиксируем после генерации PDF).
            # Поскольку в Order нет отдельных paid/completed timestamps, используем временную метку из webhook.
            paid_at_key = f"ops:paid_at:{order.id}"
            latencies_key = "ops:paid_completed_latencies"
            try:
                paid_at_value = await cache.get(paid_at_key)
                if paid_at_value is not None:
                    now_ts = datetime.now(timezone.utc).timestamp()
                    latency_seconds = max(0.0, now_ts - float(paid_at_value))
                    await cache.redis.lpush(latencies_key, latency_seconds)
                    await cache.redis.ltrim(latencies_key, 0, 999)
                    await cache.redis.expire(latencies_key, 7 * 24 * 3600)
                    await cache.delete(paid_at_key)
            except Exception as latency_exc:
                logger.warning(
                    "paid->completed latency write failed",
                    order_id=order.id,
                    error=str(latency_exc),
                )

            report_stmt = select(Report).where(Report.order_id == order.id)
            report_result = await db.execute(report_stmt)
            report = report_result.scalar_one_or_none()
            if not report:
                report = Report(order_id=order.id)
                db.add(report)

            report.pdf_path = storage.to_storage_key(generated_pdf_paths[0])
            report.chart_path = storage.to_storage_key(chart_paths[0])  # canonical chart = slot 0
            report.status = ReportStatus.ACTIVE
            report.generated_at = datetime.now(timezone.utc)

            order.status = OrderStatus.COMPLETED
            await db.commit()
            await record_analytics_event(
                db,
                event_name="order_completed",
                user_id=order.user_id,
                order_id=order.id,
                tariff_code=tariff.code,
                source_channel=source_channel,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                platform=platform,
                geo=geo,
                amount=order.amount,
                correlation_id=str(order.yookassa_id) if order.yookassa_id else None,
                cost_components={
                    "variable_cost_amount": float(order.variable_cost_amount or 0),
                    "payment_fee_amount": float(order.payment_fee_amount or 0),
                    "ai_cost_amount": float(order.ai_cost_amount or 0),
                    "infra_cost_amount": float(order.infra_cost_amount or 0),
                },
                dedupe_key=f"order_completed:{order.id}",
            )
            await record_analytics_event(
                db,
                event_name="report_generation_completed",
                user_id=order.user_id,
                order_id=order.id,
                tariff_code=tariff.code,
                source_channel=source_channel,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                platform=platform,
                geo=geo,
                dedupe_key=f"report_generation_completed:{order.id}",
            )
            if tariff.code in ADDON_REPORT_TARIFF_CODES:
                await record_analytics_event(
                    db,
                    event_name="addon_report_generation_completed",
                    user_id=order.user_id,
                    order_id=order.id,
                    tariff_code=tariff.code,
                    source_channel=source_channel,
                    utm_source=utm_source,
                    utm_medium=utm_medium,
                    utm_campaign=utm_campaign,
                    platform=platform,
                    geo=geo,
                    dedupe_key=f"addon_report_generation_completed:{order.id}",
                )

            from app.tasks.report_notifications import send_report_email_task

            try:
                send_report_email_task.delay(order.id)
            except Exception as email_queue_exc:
                logger.warning(
                    "Failed to enqueue report email notification",
                    order_id=order.id,
                    error=str(email_queue_exc),
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
                order_id=order_id,
                user_id=order.user_id,
                step=locals().get("failed_step", "unknown"),
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
            await record_analytics_event(
                db,
                event_name="report_generation_failed",
                user_id=order.user_id,
                order_id=order.id,
                source_channel=source_channel,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                platform=platform,
                geo=geo,
                notes=str(e),
                dedupe_key=f"report_generation_failed:{order.id}",
            )
            if tariff.code in ADDON_REPORT_TARIFF_CODES:
                await record_analytics_event(
                    db,
                    event_name="addon_report_generation_failed",
                    user_id=order.user_id,
                    order_id=order.id,
                    tariff_code=tariff.code,
                    source_channel=source_channel,
                    utm_source=utm_source,
                    utm_medium=utm_medium,
                    utm_campaign=utm_campaign,
                    platform=platform,
                    geo=geo,
                    notes=str(e),
                    dedupe_key=f"addon_report_generation_failed:{order.id}",
                )
            raise
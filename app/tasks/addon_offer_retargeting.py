import asyncio
from datetime import datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy import select

from app.constants.tariffs import ADDON_REPORT_TARIFF_CODES
from app.db.session import AsyncSessionLocal
from app.models.addon_offer_dispatch import AddonOfferDispatch
from app.models.order import Order
from app.models.tariff import Tariff
from app.services.addons_access import evaluate_addon_eligibility, is_addons_enabled
from app.services.analytics import get_user_attribution, record_analytics_event
from app.services.email import EmailService
from app.services.push import PushService


SUPPRESSION_REASONS = {
    "ADDONS_DISABLED",
    "NOT_ELIGIBLE",
    "ALREADY_PURCHASED",
    "OFFER_EXPIRED",
    "CHANNEL_UNAVAILABLE",
    "UNSUBSCRIBED",
    "DUPLICATE",
}


def _dispatch_key(user_id: int, parent_order_id: int, addon_code: str, channel: str, attempt_no: int) -> str:
    return f"addon-offer:{user_id}:{parent_order_id}:{addon_code}:{channel}:{attempt_no}"


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=60)
def schedule_addon_offer_followups_task(self, parent_order_id: int, user_id: int):
    return asyncio.run(_schedule_addon_offer_followups(parent_order_id=parent_order_id, user_id=user_id))


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=60)
def send_addon_offer_email_task(self, dispatch_id: int):
    return asyncio.run(_send_addon_offer_email(dispatch_id))


@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=60)
def send_addon_offer_push_task(self, dispatch_id: int):
    return asyncio.run(_send_addon_offer_push(dispatch_id))


async def _schedule_addon_offer_followups(*, parent_order_id: int, user_id: int) -> None:
    async with AsyncSessionLocal() as db:
        if not await is_addons_enabled(db):
            return

        parent_order = (
            await db.execute(select(Order).where(Order.id == parent_order_id, Order.user_id == user_id))
        ).scalar_one_or_none()
        if not parent_order:
            return

        addon_tariffs = (
            await db.execute(select(Tariff).where(Tariff.code.in_(list(ADDON_REPORT_TARIFF_CODES))))
        ).scalars().all()
        for addon_tariff in addon_tariffs:
            eligibility = await evaluate_addon_eligibility(db, user_id=user_id, addon_tariff=addon_tariff)
            if not eligibility["eligible"]:
                await _record_suppressed_event(db, user_id=user_id, addon_code=addon_tariff.code, reasons=eligibility["reasons"])
                continue

            for channel in ("email", "push"):
                for idx, delay_hours in enumerate((24, 72), start=1):
                    dedupe_key = _dispatch_key(user_id, parent_order_id, addon_tariff.code, channel, idx)
                    existing = (
                        await db.execute(select(AddonOfferDispatch).where(AddonOfferDispatch.dedupe_key == dedupe_key))
                    ).scalar_one_or_none()
                    if existing:
                        continue

                    scheduled_at = datetime.now(timezone.utc) + timedelta(hours=delay_hours)
                    row = AddonOfferDispatch(
                        user_id=user_id,
                        parent_order_id=parent_order_id,
                        addon_code=addon_tariff.code,
                        channel=channel,
                        attempt_no=idx,
                        scheduled_at=scheduled_at,
                        status="scheduled",
                        dedupe_key=dedupe_key,
                        payload={"delay_hours": delay_hours},
                    )
                    db.add(row)
                    await db.flush()
                    if channel == "email":
                        send_addon_offer_email_task.delay(row.id)
                        event_name = "addon_offer_email_scheduled"
                    else:
                        send_addon_offer_push_task.delay(row.id)
                        event_name = "addon_offer_push_scheduled"
                    utm_source, utm_medium, utm_campaign, source_channel, platform, geo = await get_user_attribution(db, user_id)
                    await record_analytics_event(
                        db,
                        event_name=event_name,
                        user_id=user_id,
                        order_id=parent_order_id,
                        tariff_code=addon_tariff.code,
                        source_channel=source_channel,
                        utm_source=utm_source,
                        utm_medium=utm_medium,
                        utm_campaign=utm_campaign,
                        platform=platform,
                        geo=geo,
                        dedupe_key=f"{event_name}:{row.id}",
                    )
        await db.commit()


async def _send_addon_offer_email(dispatch_id: int) -> None:
    async with AsyncSessionLocal() as db:
        dispatch = (
            await db.execute(select(AddonOfferDispatch).where(AddonOfferDispatch.id == dispatch_id))
        ).scalar_one_or_none()
        if not dispatch or dispatch.status != "scheduled":
            return
        if not await is_addons_enabled(db):
            dispatch.status = "skipped"
            dispatch.skip_reason = "ADDONS_DISABLED"
            await db.commit()
            return

        addon_tariff = (await db.execute(select(Tariff).where(Tariff.code == dispatch.addon_code))).scalar_one_or_none()
        if not addon_tariff:
            dispatch.status = "skipped"
            dispatch.skip_reason = "NOT_ELIGIBLE"
            await db.commit()
            return
        eligibility = await evaluate_addon_eligibility(db, user_id=dispatch.user_id, addon_tariff=addon_tariff)
        if not eligibility["eligible"]:
            dispatch.status = "skipped"
            dispatch.skip_reason = eligibility["reasons"][0] if eligibility["reasons"] else "NOT_ELIGIBLE"
            await _record_suppressed_event(db, user_id=dispatch.user_id, addon_code=dispatch.addon_code, reasons=eligibility["reasons"])
            await db.commit()
            return

        order = (await db.execute(select(Order).where(Order.id == dispatch.parent_order_id))).scalar_one_or_none()
        if not order:
            dispatch.status = "skipped"
            dispatch.skip_reason = "NOT_ELIGIBLE"
            await db.commit()
            return

        email_service = EmailService()
        recipient = order.report_delivery_email
        if not recipient:
            dispatch.status = "skipped"
            dispatch.skip_reason = "CHANNEL_UNAVAILABLE"
            await db.commit()
            return
        try:
            await email_service.send_email(
                recipients=[recipient],
                subject=f"Дополните отчет: {addon_tariff.name}",
                body="",
                template_name=None,
                template_body=None,
            )
            dispatch.status = "sent"
            dispatch.sent_at = datetime.now(timezone.utc)
            utm_source, utm_medium, utm_campaign, source_channel, platform, geo = await get_user_attribution(db, dispatch.user_id)
            await record_analytics_event(
                db,
                event_name="addon_offer_email_sent",
                user_id=dispatch.user_id,
                order_id=dispatch.parent_order_id,
                tariff_code=dispatch.addon_code,
                source_channel=source_channel,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                platform=platform,
                geo=geo,
                dedupe_key=f"addon_offer_email_sent:{dispatch.id}",
            )
        except Exception:
            dispatch.status = "failed"
            dispatch.skip_reason = "CHANNEL_UNAVAILABLE"
            utm_source, utm_medium, utm_campaign, source_channel, platform, geo = await get_user_attribution(db, dispatch.user_id)
            await record_analytics_event(
                db,
                event_name="addon_offer_send_failed",
                user_id=dispatch.user_id,
                order_id=dispatch.parent_order_id,
                tariff_code=dispatch.addon_code,
                source_channel=source_channel,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                platform=platform,
                geo=geo,
                event_metadata={"channel": "email"},
                dedupe_key=f"addon_offer_send_failed:email:{dispatch.id}",
            )
            raise
        finally:
            await db.commit()


async def _send_addon_offer_push(dispatch_id: int) -> None:
    async with AsyncSessionLocal() as db:
        dispatch = (
            await db.execute(select(AddonOfferDispatch).where(AddonOfferDispatch.id == dispatch_id))
        ).scalar_one_or_none()
        if not dispatch or dispatch.status != "scheduled":
            return
        if not await is_addons_enabled(db):
            dispatch.status = "skipped"
            dispatch.skip_reason = "ADDONS_DISABLED"
            await db.commit()
            return

        addon_tariff = (await db.execute(select(Tariff).where(Tariff.code == dispatch.addon_code))).scalar_one_or_none()
        if not addon_tariff:
            dispatch.status = "skipped"
            dispatch.skip_reason = "NOT_ELIGIBLE"
            await db.commit()
            return
        eligibility = await evaluate_addon_eligibility(db, user_id=dispatch.user_id, addon_tariff=addon_tariff)
        if not eligibility["eligible"]:
            dispatch.status = "skipped"
            dispatch.skip_reason = eligibility["reasons"][0] if eligibility["reasons"] else "NOT_ELIGIBLE"
            await _record_suppressed_event(db, user_id=dispatch.user_id, addon_code=dispatch.addon_code, reasons=eligibility["reasons"])
            await db.commit()
            return

        try:
            push_service = PushService()
            await push_service.send_push(
                user_id=dispatch.user_id,
                title="Доступен add-on к вашему отчету",
                body=f"Откройте {addon_tariff.name} в кабинете",
                deep_link="/dashboard/reports",
            )
            dispatch.status = "sent"
            dispatch.sent_at = datetime.now(timezone.utc)
            utm_source, utm_medium, utm_campaign, source_channel, platform, geo = await get_user_attribution(db, dispatch.user_id)
            await record_analytics_event(
                db,
                event_name="addon_offer_push_sent",
                user_id=dispatch.user_id,
                order_id=dispatch.parent_order_id,
                tariff_code=dispatch.addon_code,
                source_channel=source_channel,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                platform=platform,
                geo=geo,
                dedupe_key=f"addon_offer_push_sent:{dispatch.id}",
            )
        except Exception:
            dispatch.status = "failed"
            dispatch.skip_reason = "CHANNEL_UNAVAILABLE"
            utm_source, utm_medium, utm_campaign, source_channel, platform, geo = await get_user_attribution(db, dispatch.user_id)
            await record_analytics_event(
                db,
                event_name="addon_offer_send_failed",
                user_id=dispatch.user_id,
                order_id=dispatch.parent_order_id,
                tariff_code=dispatch.addon_code,
                source_channel=source_channel,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                platform=platform,
                geo=geo,
                event_metadata={"channel": "push"},
                dedupe_key=f"addon_offer_send_failed:push:{dispatch.id}",
            )
            raise
        finally:
            await db.commit()


async def _record_suppressed_event(db, *, user_id: int, addon_code: str, reasons: list[str]) -> None:
    normalized = [r for r in reasons if r in SUPPRESSION_REASONS] or ["NOT_ELIGIBLE"]
    utm_source, utm_medium, utm_campaign, source_channel, platform, geo = await get_user_attribution(db, user_id)
    await record_analytics_event(
        db,
        event_name="addon_offer_suppressed",
        user_id=user_id,
        tariff_code=addon_code,
        source_channel=source_channel,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        platform=platform,
        geo=geo,
        event_metadata={"reasons": normalized},
        dedupe_key=f"addon_offer_suppressed:{user_id}:{addon_code}:{':'.join(normalized)}",
    )

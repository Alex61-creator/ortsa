import asyncio
from datetime import datetime, timedelta, timezone
from celery import shared_task
from sqlalchemy import update, select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.order import Order, OrderStatus
from app.models.report import Report, ReportStatus
from app.models.synastry_report import SynastryReport, SynastryStatus
from app.models.tariff import Tariff
from app.services.storage import StorageService

@shared_task
def cancel_expired_orders():
    return asyncio.run(_cancel_expired_orders_async())

async def _cancel_expired_orders_async():
    async with AsyncSessionLocal() as db:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        stmt = update(Order).where(
            Order.status == OrderStatus.PENDING,
            Order.created_at < cutoff
        ).values(status=OrderStatus.CANCELED)
        result = await db.execute(stmt)
        await db.commit()
        return {"canceled": result.rowcount}

@shared_task
def cleanup_storage():
    return asyncio.run(_cleanup_storage_async())

async def _cleanup_storage_async():
    async with AsyncSessionLocal() as db:
        storage = StorageService()
        now_utc = datetime.now(timezone.utc)
        deleted = 0
        archived_reports = 0
        archived_synastry = 0

        report_stmt = (
            select(Report, Order, Tariff)
            .join(Order, Order.id == Report.order_id)
            .join(Tariff, Tariff.id == Order.tariff_id)
            .where(Report.status == ReportStatus.ACTIVE, Report.generated_at.is_not(None))
            .limit(500)
        )
        report_rows = (await db.execute(report_stmt)).all()
        for report, _order, tariff in report_rows:
            retention_days = getattr(tariff, "retention_days", None) or settings.STORAGE_RETENTION_DAYS
            expires_at = report.generated_at + timedelta(days=retention_days)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at > now_utc:
                continue
            if await storage.delete_if_expired(report.pdf_path, expires_at):
                deleted += 1
            if await storage.delete_if_expired(report.chart_path, expires_at):
                deleted += 1
            report.pdf_path = None
            report.chart_path = None
            report.status = ReportStatus.ARCHIVED
            archived_reports += 1

        syn_stmt = (
            select(SynastryReport)
            .where(SynastryReport.status == SynastryStatus.COMPLETED, SynastryReport.expires_at.is_not(None))
            .limit(500)
        )
        syn_rows = (await db.execute(syn_stmt)).scalars().all()
        for report in syn_rows:
            expires_at = report.expires_at
            exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
            if exp > now_utc:
                continue
            if await storage.delete_if_expired(report.pdf_path, exp):
                deleted += 1
            if await storage.delete_if_expired(report.chart_path, exp):
                deleted += 1
            report.pdf_path = None
            report.chart_path = None
            report.status = SynastryStatus.ARCHIVED
            archived_synastry += 1

        await db.commit()
        return {
            "deleted_files": deleted,
            "archived_reports": archived_reports,
            "archived_synastry": archived_synastry,
        }
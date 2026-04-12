import asyncio
from datetime import datetime, timedelta
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.order import Order, OrderStatus
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
    storage = StorageService()
    deleted = await storage.cleanup_old_files(settings.STORAGE_RETENTION_DAYS)
    return {"deleted_files": deleted}
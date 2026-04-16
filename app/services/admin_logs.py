from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_action_log import AdminActionLog


async def append_admin_log(
    db: AsyncSession,
    actor_email: str,
    action: str,
    entity: str,
    *,
    details: dict | None = None,
) -> AdminActionLog:
    row = AdminActionLog(
        id=str(uuid4()),
        actor_email=actor_email,
        action=action,
        entity=entity,
        details=details,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def list_admin_logs(
    db: AsyncSession,
    *,
    actor_email: str | None = None,
    action: str | None = None,
    entity: str | None = None,
    limit: int = 300,
) -> list[AdminActionLog]:
    stmt = select(AdminActionLog).order_by(AdminActionLog.created_at.desc()).limit(limit)
    if actor_email:
        stmt = stmt.where(AdminActionLog.actor_email.ilike(f"%{actor_email}%"))
    if action:
        stmt = stmt.where(AdminActionLog.action.ilike(f"%{action}%"))
    if entity:
        stmt = stmt.where(AdminActionLog.entity.ilike(f"%{entity}%"))
    result = await db.execute(stmt)
    return result.scalars().all()

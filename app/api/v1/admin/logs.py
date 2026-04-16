from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_extra import AdminLogRow
from app.services.admin_logs import append_admin_log as append_admin_log_db
from app.services.admin_logs import list_admin_logs

router = APIRouter()


async def append_admin_log(
    db: AsyncSession,
    actor_email: str,
    action: str,
    entity: str,
    *,
    details: dict | None = None,
) -> None:
    await append_admin_log_db(db, actor_email, action, entity, details=details)


@router.get("/", response_model=list[AdminLogRow], summary="Лог действий администратора")
async def list_logs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    actor: str | None = Query(default=None),
    action: str | None = Query(default=None),
    entity: str | None = Query(default=None),
    limit: int = Query(default=300, ge=1, le=1000),
):
    rows = await list_admin_logs(db, actor_email=actor, action=action, entity=entity, limit=limit)
    if rows:
        return [AdminLogRow.model_validate(row) for row in rows]
    return [
        AdminLogRow(
            id="bootstrap-log-seed",
            actor_email="admin@astrogen.local",
            action="bootstrap_log_seed",
            entity="system",
            created_at=datetime.utcnow(),
            details={"note": "No actions yet"},
        )
    ]

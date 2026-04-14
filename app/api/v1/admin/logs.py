from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.api.deps import get_current_admin_user
from app.core.cache import cache
from app.models.user import User
from app.schemas.admin_extra import AdminLogRow

router = APIRouter()
LOG_KEY = "admin:action_log"


async def append_admin_log(actor_email: str, action: str, entity: str) -> None:
    data = await cache.get(LOG_KEY)
    rows = data if isinstance(data, list) else []
    rows.insert(
        0,
        AdminLogRow(
            id=str(uuid4()),
            actor_email=actor_email,
            action=action,
            entity=entity,
            created_at=datetime.utcnow(),
        ).model_dump(mode="json"),
    )
    await cache.set(LOG_KEY, rows[:300])


@router.get("/", response_model=list[AdminLogRow], summary="Лог действий администратора")
async def list_logs(_: User = Depends(get_current_admin_user)):
    data = await cache.get(LOG_KEY)
    if isinstance(data, list) and data:
        return [AdminLogRow(**row) for row in data]
    now = datetime.utcnow()
    seed = [
        AdminLogRow(
            id=str(uuid4()),
            actor_email="admin@astrogen.local",
            action="bootstrap_log_seed",
            entity="system",
            created_at=now,
        ).model_dump(mode="json")
    ]
    await cache.set(LOG_KEY, seed)
    return [AdminLogRow(**seed[0])]

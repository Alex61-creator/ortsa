from fastapi import APIRouter, Depends
from datetime import datetime, timezone
import asyncio

from app.api.deps import get_current_admin_user
from app.models.user import User
from app.schemas.admin_extra import AdminTaskRow
from app.tasks.worker import celery_app

router = APIRouter()


@router.get("/", response_model=list[AdminTaskRow], summary="Задачи Celery (админ)")
async def list_tasks(_: User = Depends(get_current_admin_user)):
    now = datetime.now(timezone.utc)

    async def _inspect() -> dict:
        def _run() -> dict:
            inspect = celery_app.control.inspect(timeout=1)
            return {
                "active": inspect.active() or {},
                "reserved": inspect.reserved() or {},
                "scheduled": inspect.scheduled() or {},
            }

        return await asyncio.to_thread(_run)

    try:
        snapshot = await _inspect()
    except Exception as exc:
        return [
            AdminTaskRow(
                id="celery-unavailable",
                queue="system",
                name="celery.inspect",
                status="degraded",
                created_at=now,
                updated_at=now,
                worker=None,
                error=str(exc),
            )
        ]

    rows: list[AdminTaskRow] = []
    for worker_name, items in snapshot.get("active", {}).items():
        for item in items:
            rows.append(
                AdminTaskRow(
                    id=item.get("id") or f"{worker_name}-active",
                    queue=item.get("delivery_info", {}).get("routing_key") or item.get("name", "default"),
                    name=item.get("name", "unknown"),
                    status="running",
                    created_at=now,
                    updated_at=now,
                    worker=worker_name,
                )
            )
    for worker_name, items in snapshot.get("reserved", {}).items():
        for item in items:
            rows.append(
                AdminTaskRow(
                    id=item.get("id") or f"{worker_name}-reserved",
                    queue=item.get("delivery_info", {}).get("routing_key") or item.get("name", "default"),
                    name=item.get("name", "unknown"),
                    status="pending",
                    created_at=now,
                    updated_at=now,
                    worker=worker_name,
                )
            )
    for worker_name, items in snapshot.get("scheduled", {}).items():
        for item in items:
            request = item.get("request", {})
            eta = item.get("eta")
            created_at = now
            if eta:
                try:
                    created_at = datetime.fromisoformat(str(eta).replace("Z", "+00:00"))
                except ValueError:
                    created_at = now
            rows.append(
                AdminTaskRow(
                    id=request.get("id") or f"{worker_name}-scheduled",
                    queue=request.get("delivery_info", {}).get("routing_key") or request.get("name", "default"),
                    name=request.get("name", "unknown"),
                    status="scheduled",
                    created_at=created_at,
                    updated_at=now,
                    worker=worker_name,
                )
            )
    if rows:
        return rows
    return [
        AdminTaskRow(
            id="celery-idle",
            queue="system",
            name="No active tasks",
            status="idle",
            created_at=now,
            updated_at=now,
            worker=None,
        )
    ]

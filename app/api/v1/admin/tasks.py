from datetime import datetime, timedelta

from fastapi import APIRouter, Depends

from app.api.deps import get_current_admin_user
from app.models.user import User
from app.schemas.admin_extra import AdminTaskRow

router = APIRouter()


@router.get("/", response_model=list[AdminTaskRow], summary="Задачи Celery (админ)")
async def list_tasks(_: User = Depends(get_current_admin_user)):
    now = datetime.utcnow()
    return [
        AdminTaskRow(
            id="task-report-1",
            queue="reports",
            name="generate_report_task",
            status="running",
            created_at=now - timedelta(minutes=3),
            updated_at=now,
        ),
        AdminTaskRow(
            id="task-mail-2",
            queue="emails",
            name="send_report_email",
            status="completed",
            created_at=now - timedelta(minutes=10),
            updated_at=now - timedelta(minutes=8),
        ),
        AdminTaskRow(
            id="task-retry-3",
            queue="reports",
            name="retry_failed_report",
            status="failed",
            created_at=now - timedelta(minutes=24),
            updated_at=now - timedelta(minutes=20),
        ),
        AdminTaskRow(
            id="task-wait-4",
            queue="reports",
            name="generate_report_task",
            status="pending",
            created_at=now - timedelta(minutes=2),
            updated_at=now - timedelta(minutes=2),
        ),
    ]

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.core.health_checks import assert_dependencies_ready
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin_extra import HealthWidget

router = APIRouter()


@router.get("/", response_model=list[HealthWidget], summary="Мониторинг: карточки статуса")
async def health_widgets(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    ready = await assert_dependencies_ready(db)
    return [
        HealthWidget(name="API", status="ok", value="online"),
        HealthWidget(name="PostgreSQL", status="ok" if ready.get("database") else "error", value="connected"),
        HealthWidget(name="Redis", status="ok" if ready.get("redis") else "error", value="connected"),
    ]

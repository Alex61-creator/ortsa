from typing import Literal, Optional

from pydantic import BaseModel


class Message(BaseModel):
    message: str


class StatusOk(BaseModel):
    """Унифицированный ответ «успешно обработано» (вебхуки, служебные действия)."""

    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    """Ответ readiness: БД + Redis; опционально Celery (если HEALTH_CHECK_CELERY=true)."""

    status: Literal["ok"] = "ok"
    celery_workers_ok: Optional[bool] = None
    celery_queue_length: Optional[int] = None
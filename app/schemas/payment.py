from typing import Any, Optional

from pydantic import BaseModel


class YookassaWebhookPayload(BaseModel):
    """Базовая схема тела webhook ЮKassa; расширяйте под фактические event/object."""

    type: Optional[str] = None
    event: Optional[str] = None
    object: Optional[dict[str, Any]] = None

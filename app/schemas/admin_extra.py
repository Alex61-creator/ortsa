from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class FunnelStep(BaseModel):
    key: str
    title: str
    count: int
    conversion_pct: float


class FunnelSummary(BaseModel):
    period: str
    steps: list[FunnelStep]
    drop_offs: list[dict] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class AdminPaymentRow(BaseModel):
    order_id: int
    user_id: int
    user_email: str
    status: str
    amount: Decimal
    tariff_name: str
    created_at: datetime


class AdminTaskRow(BaseModel):
    id: str
    queue: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime


class PromoOut(BaseModel):
    id: str
    code: str
    discount_percent: int = Field(ge=1, le=100)
    max_uses: int = Field(ge=1)
    used_count: int = Field(ge=0)
    active_until: Optional[datetime] = None
    is_active: bool


class PromoCreate(BaseModel):
    code: str
    discount_percent: int = Field(ge=1, le=100)
    max_uses: int = Field(ge=1, default=100)
    active_until: Optional[datetime] = None


class PromoPatch(BaseModel):
    discount_percent: Optional[int] = Field(default=None, ge=1, le=100)
    max_uses: Optional[int] = Field(default=None, ge=1)
    active_until: Optional[datetime] = None
    is_active: Optional[bool] = None


class FlagOut(BaseModel):
    key: str
    description: str
    enabled: bool


class FlagPatch(BaseModel):
    enabled: bool


class HealthWidget(BaseModel):
    name: str
    status: str
    value: str


class AdminLogRow(BaseModel):
    id: str
    actor_email: str
    action: str
    entity: str
    created_at: datetime


class UserNoteOut(BaseModel):
    id: str
    text: str
    created_at: datetime


class UserNoteCreate(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class TariffHistoryRow(BaseModel):
    id: str
    tariff_id: int
    actor: str
    payload: dict
    created_at: datetime


from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.order import OrderListItem


class DashboardSubscriptionBrief(BaseModel):
    tariff_name: str
    tariff_code: str
    status: str
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False


class DashboardSummaryOut(BaseModel):
    natal_count: int = Field(description="Количество сохранённых натальных карт")
    reports_ready_count: int = Field(description="Заказов с готовым PDF/отчётом")
    subscription: DashboardSubscriptionBrief | None = None
    recent_orders: list[OrderListItem] = Field(default_factory=list, description="Последние заказы (до 5)")

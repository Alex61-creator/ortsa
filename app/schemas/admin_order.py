from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.order import TariffSummary


class AdminOrderListItem(BaseModel):
    id: int
    user_id: int
    status: str
    amount: Decimal
    natal_data_id: int | None
    created_at: datetime
    updated_at: datetime
    tariff: TariffSummary
    report_ready: bool

    class Config:
        from_attributes = True

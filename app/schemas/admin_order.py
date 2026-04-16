from datetime import datetime
from decimal import Decimal
from typing import Any

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
    promo_code: str | None = None
    report_option_flags: dict[str, Any] | None = None
    report_options_line_amount: Decimal | None = None

    class Config:
        from_attributes = True

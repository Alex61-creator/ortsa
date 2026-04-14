from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class AdminUserListItem(BaseModel):
    id: int
    email: str
    oauth_provider: str
    is_admin: bool
    created_at: datetime
    consent_given_at: Optional[datetime] = None
    # Enriched aggregated fields
    total_spent: Decimal = Decimal("0.00")
    orders_count: int = 0
    last_order_at: Optional[datetime] = None
    blocked: bool = False
    latest_tariff_name: Optional[str] = None
    latest_tariff_code: Optional[str] = None

    model_config = {"from_attributes": True}


class AdminUserOut(BaseModel):
    id: int
    email: str
    oauth_provider: str
    external_id: str
    is_admin: bool
    created_at: datetime
    consent_given_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

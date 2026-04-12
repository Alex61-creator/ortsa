from pydantic import BaseModel
from decimal import Decimal
from typing import Any


class TariffPublicOut(BaseModel):
    code: str
    name: str
    price: Decimal
    price_usd: Decimal
    compare_price_usd: Decimal | None = None
    annual_total_usd: Decimal | None = None
    features: dict[str, Any]
    retention_days: int
    priority: int
    billing_type: str = "one_time"
    subscription_interval: str | None = None
    llm_tier: str
    max_natal_profiles: int

    class Config:
        from_attributes = True

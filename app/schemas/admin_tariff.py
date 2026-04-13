from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


class TariffAdminOut(BaseModel):
    id: int
    code: str
    name: str
    price: Decimal
    price_usd: Decimal
    compare_price_usd: Optional[Decimal] = None
    annual_total_usd: Optional[Decimal] = None
    features: dict[str, Any]
    retention_days: int
    priority: int
    billing_type: str
    subscription_interval: Optional[str] = None
    llm_tier: str

    class Config:
        from_attributes = True


class TariffAdminPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[Decimal] = None
    price_usd: Optional[Decimal] = None
    compare_price_usd: Optional[Decimal] = None
    annual_total_usd: Optional[Decimal] = None
    features: Optional[dict[str, Any]] = None
    retention_days: Optional[int] = Field(default=None, ge=0)
    priority: Optional[int] = None
    billing_type: Optional[str] = None
    subscription_interval: Optional[str] = None
    llm_tier: Optional[str] = None

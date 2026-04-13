from pydantic import BaseModel, Field, EmailStr
from decimal import Decimal
from datetime import datetime
from typing import Optional


class OrderCreate(BaseModel):
    tariff_code: str
    natal_data_id: int
    report_delivery_email: Optional[EmailStr] = Field(
        default=None,
        description="Email для PDF и фискального чека; обязателен, если у аккаунта нет реальной почты (Telegram / OAuth без email).",
    )


class TariffSummary(BaseModel):
    code: str
    name: str
    billing_type: str = "one_time"
    subscription_interval: str | None = None

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    user_id: int
    natal_data_id: int | None
    tariff_id: int
    status: str
    amount: Decimal
    yookassa_id: str | None
    confirmation_url: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrderListItem(BaseModel):
    id: int
    status: str
    amount: Decimal
    natal_data_id: int | None
    created_at: datetime
    updated_at: datetime
    tariff: TariffSummary
    report_ready: bool = Field(
        description="True если отчёт сгенерирован и доступен для скачивания"
    )

    class Config:
        from_attributes = True


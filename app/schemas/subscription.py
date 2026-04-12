from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.subscription import SubscriptionStatus


def subscription_status_message(status: str, cancel_at_period_end: bool) -> str | None:
    """Короткое пояснение для UI (кабинет / SPA)."""
    if status == SubscriptionStatus.PAST_DUE.value:
        return (
            "Не удалось списать оплату по подписке. Обновите способ оплаты в личном кабинете."
        )
    if status == SubscriptionStatus.ACTIVE.value and cancel_at_period_end:
        return (
            "Подписка активна до конца оплаченного периода; автопродление отключено."
        )
    if status == SubscriptionStatus.CANCELED.value:
        return "Подписка отменена."
    return None


class SubscriptionOut(BaseModel):
    id: int
    tariff_code: str
    tariff_name: str
    status: str
    amount: Decimal
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    status_message: str | None = None

    class Config:
        from_attributes = True

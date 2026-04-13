from decimal import Decimal

from pydantic import BaseModel, Field


class AdminRefundResponse(BaseModel):
    """Ответ после инициации возврата в ЮKassa (админский API)."""

    refund_id: str = Field(description="Идентификатор возврата в ЮKassa")
    status: str = Field(description="Статус возврата")
    amount: Decimal = Field(description="Сумма возврата")

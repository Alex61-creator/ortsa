from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class LlmUsageLog(TimestampMixin, Base):
    __tablename__ = "llm_usage_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Имя модели (deepseek-chat, grok-4.20, claude-sonnet-4-6 …)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    # Провайдер: deepseek | grok | claude
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="deepseek", index=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    # Токены из prompt cache провайдера (Claude ephemeral cache)
    cached_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    cost_rub: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)

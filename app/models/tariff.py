from sqlalchemy import String, Integer, Numeric, JSON
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Tariff(Base):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    compare_price_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    annual_total_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    # Ожидаемые ключи: max_natal_profiles (int) — лимит сохранённых карт в кабинете.
    features: Mapped[dict] = mapped_column(JSON, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    # one_time — разовая оплата; subscription — первый платёж с сохранением карты (Astro Pro)
    billing_type: Mapped[str] = mapped_column(String(20), default="one_time", nullable=False)
    subscription_interval: Mapped[str | None] = mapped_column(String(20), nullable=True)  # month | year
    # Уровень промпта LLM: free | natal_full | pro (не путать с code тарифа)
    llm_tier: Mapped[str] = mapped_column(String(20), default="natal_full", nullable=False)
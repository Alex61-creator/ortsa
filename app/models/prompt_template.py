from sqlalchemy import String, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.base import Base


class LlmPromptTemplate(Base):
    """Редактируемая статическая часть системного промпта LLM, хранимая в БД.

    Ключ уникальности: (tariff_code, locale, llm_provider).
    llm_provider=NULL → шаблон для всех провайдеров (обратная совместимость).
    Поиск: сначала (code, locale, provider), затем (code, locale, NULL), затем хардкод.
    """
    __tablename__ = "llm_prompt_templates"
    __table_args__ = (
        UniqueConstraint("tariff_code", "locale", "llm_provider", name="uq_llm_prompt_code_locale_provider"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tariff_code: Mapped[str] = mapped_column(String(20), nullable=False)
    locale: Mapped[str] = mapped_column(String(5), nullable=False)
    # Провайдер: deepseek | grok | claude | NULL (все)
    llm_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

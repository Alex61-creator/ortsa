from sqlalchemy import String, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.base import Base


class LlmPromptTemplate(Base):
    """Редактируемая статическая часть системного промпта LLM, хранимая в БД.

    Ключ уникальности: (tariff_code, locale).
    Если записи нет — LLMService откатывается на захардкоженный промпт из llm.py.
    """
    __tablename__ = "llm_prompt_templates"
    __table_args__ = (
        UniqueConstraint("tariff_code", "locale", name="uq_llm_prompt_code_locale"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Код тарифа: free | report | bundle | sub_monthly | sub_annual
    tariff_code: Mapped[str] = mapped_column(String(20), nullable=False)
    # Язык: ru | en
    locale: Mapped[str] = mapped_column(String(5), nullable=False)
    # Статическая часть системного промпта (редактируется в админ-панели)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

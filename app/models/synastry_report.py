"""Модель синастрии — совместность двух натальных карт."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SynastryStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    FAILED = "failed"


class SynastryReport(Base):
    """
    Хранит синастрию (совместность) между двумя натальными профилями.

    Anti-abuse:
    - input_hash        — MD5 двух натальных профилей; если хэш не изменился,
                          новый отчёт не генерируется (возвращается существующий PDF)
    - next_regen_allowed_at — cooldown перед следующей регенерацией
    - generation_count  — общее число генераций; для bundle ограничено константой
    """

    __tablename__ = "synastry_reports"
    __table_args__ = (
        # Уникальная пара профилей для одного пользователя (порядок нормализован: id_1 < id_2)
        UniqueConstraint("user_id", "natal_data_id_1", "natal_data_id_2", name="uq_synastry_user_pair"),
        Index("ix_synastry_reports_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # id_1 < id_2 всегда (нормализация в сервисе)
    natal_data_id_1: Mapped[int] = mapped_column(
        ForeignKey("natal_data.id", ondelete="RESTRICT"), nullable=False
    )
    natal_data_id_2: Mapped[int] = mapped_column(
        ForeignKey("natal_data.id", ondelete="RESTRICT"), nullable=False
    )

    status: Mapped[str] = mapped_column(String(20), nullable=False, default=SynastryStatus.PENDING)
    locale: Mapped[str] = mapped_column(String(5), nullable=False, default="ru")

    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    chart_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Anti-abuse ────────────────────────────────────────────────────────────
    generation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_regen_allowed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # MD5(natal_1_fields || natal_2_fields) — если совпадает, отдаём кэш
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Провайдер, которым сгенерирован отчёт: deepseek | grok | claude
    llm_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.utcnow(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    natal_data_1 = relationship("NatalData", foreign_keys=[natal_data_id_1])
    natal_data_2 = relationship("NatalData", foreign_keys=[natal_data_id_2])

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AnnualProgressionLog(Base):
    """Идемпотентность ежегодных отчётов по прогрессиям.

    Одна запись на подписку и год жизни (year).
    """

    __tablename__ = "annual_progression_logs"
    __table_args__ = (
        UniqueConstraint("subscription_id", "year", name="uq_progression_sub_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False, comment="Год жизни пользователя")
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    subscription = relationship("Subscription", backref="annual_progression_logs")

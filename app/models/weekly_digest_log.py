from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WeeklyDigestLog(Base):
    """Идемпотентность еженедельных дайджестов транзитов.

    Одна запись на подписку и дату начала недели (понедельник).
    """

    __tablename__ = "weekly_digest_logs"
    __table_args__ = (
        UniqueConstraint("subscription_id", "week_start", name="uq_weekly_sub_week"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False, comment="Понедельник недели")
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    subscription = relationship("Subscription", backref="weekly_digest_logs")

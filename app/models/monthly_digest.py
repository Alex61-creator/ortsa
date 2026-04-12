from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MonthlyDigestLog(Base):
    """Идемпотентность ежемесячной рассылки для подписки Pro (одна запись на подписку и месяц)."""

    __tablename__ = "monthly_digest_logs"
    __table_args__ = (UniqueConstraint("subscription_id", "period_yyyymm", name="uq_digest_sub_period"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    period_yyyymm: Mapped[str] = mapped_column(String(7), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    subscription = relationship("Subscription", backref="monthly_digest_logs")

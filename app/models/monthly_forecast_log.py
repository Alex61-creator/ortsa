from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MonthlyForecastLog(Base):
    """Идемпотентность ежемесячных персональных прогнозов.

    Одна запись на подписку и месяц (period_yyyymm).
    Гарантирует, что прогноз не будет отправлен дважды даже при повторном срабатывании Celery beat.
    """

    __tablename__ = "monthly_forecast_logs"
    __table_args__ = (
        UniqueConstraint("subscription_id", "period_yyyymm", name="uq_forecast_sub_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    period_yyyymm: Mapped[str] = mapped_column(String(7), nullable=False, comment="Формат: 2026-04")
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    subscription = relationship("Subscription", backref="monthly_forecast_logs")

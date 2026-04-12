from sqlalchemy import String, Float, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.db.base import Base

class NatalData(Base):
    __tablename__ = "natal_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(80), nullable=False)
    birth_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    birth_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    birth_place: Mapped[str] = mapped_column(String(120), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False)
    house_system: Mapped[str] = mapped_column(String(20), default="P")
    report_locale: Mapped[str] = mapped_column(String(5), default="ru", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", backref="natal_data")
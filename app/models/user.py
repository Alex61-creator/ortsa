from sqlalchemy import String, Boolean, DateTime, Integer, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.base import Base
import enum

class OAuthProvider(str, enum.Enum):
    GOOGLE = "google"
    YANDEX = "yandex"
    APPLE = "apple"
    TELEGRAM = "telegram"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    oauth_provider: Mapped[OAuthProvider] = mapped_column(SQLEnum(OAuthProvider), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    privacy_policy_version: Mapped[str] = mapped_column(String(20), default="1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
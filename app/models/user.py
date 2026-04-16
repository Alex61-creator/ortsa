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
    # Minimal RBAC for dangerous admin operations.
    # `None` means "legacy admin": allow by default to avoid breaking existing setups.
    can_refund: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    can_retry_report: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    can_resend_report_email: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    can_manual_override: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    privacy_policy_version: Mapped[str] = mapped_column(String(20), default="1.0")
    utm_source: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    utm_medium: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_channel: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    signup_platform: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    signup_geo: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    acquisition_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
"""Per-user override настроек синастрии (устанавливается администратором)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserSynastryOverride(Base):
    """
    Позволяет администратору:
    - включить синастрию для любого пользователя вне зависимости от тарифа
    - выдать дополнительные бесплатные генерации
    - оставить внутреннюю заметку
    """

    __tablename__ = "user_synastry_overrides"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # Принудительно включить синастрию (независимо от тарифа)
    synastry_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Сколько бесплатных синастрий выдано администратором (дополнительно к тарифным)
    free_synastries_granted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Внутренняя заметка администратора
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship("User", backref="synastry_override")

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrderIdempotencyState(str, enum.Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OrderIdempotency(Base):
    __tablename__ = "order_idempotency"

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_order_idempotency_user_idempotency_key"),
        Index("ix_order_idempotency_user_id", "user_id"),
        Index("ix_order_idempotency_state", "state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)

    # lifecycle идемпотентности именно HTTP-запроса create_order:
    # processing/completed/failed
    state: Mapped[OrderIdempotencyState] = mapped_column(
        SQLEnum(
            OrderIdempotencyState,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            name="orderidempotencystate",
        ),
        nullable=False,
        default=OrderIdempotencyState.PROCESSING,
    )

    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )

    yookassa_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confirmation_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    http_status: Mapped[int | None] = mapped_column(nullable=True)
    error_detail: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


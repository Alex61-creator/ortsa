from sqlalchemy import String, ForeignKey, DateTime, Numeric, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from decimal import Decimal
from app.db.base import Base
import enum

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    FAILED_TO_INIT_PAYMENT = "failed_to_init_payment"
    PAID = "paid"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELED = "canceled"

class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_user_id", "user_id"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_created_at", "created_at"),
        Index("ix_orders_user_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    natal_data_id: Mapped[int | None] = mapped_column(
        ForeignKey("natal_data.id", ondelete="RESTRICT"), nullable=True
    )
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id"), nullable=False)
    # Используем `.value` (pending/paid/failed), чтобы SQLAlchemy корректно маппило значения
    # при работе с не-native enum (SQLite и т.п.). Иначе возможна ситуация,
    # когда в БД хранятся enum "имена" (PAID/FAILED), а ORM возвращает неверное значение.
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=OrderStatus.PENDING,
        nullable=False,
    )
    yookassa_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    refund_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    refund_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    report_delivery_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    promo_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    payment_provider: Mapped[str | None] = mapped_column(String(50), nullable=True, default="yookassa")
    variable_cost_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    payment_fee_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    ai_cost_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    infra_cost_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="orders")
    natal_data = relationship("NatalData", backref="orders")
    tariff = relationship("Tariff", backref="orders")
    report = relationship("Report", back_populates="order", uselist=False)
    natal_items = relationship("OrderNatalItem", cascade="all, delete-orphan", order_by="OrderNatalItem.slot_index")
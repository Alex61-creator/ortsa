from sqlalchemy import String, ForeignKey, DateTime, Numeric, Enum as SQLEnum
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

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    natal_data_id: Mapped[int | None] = mapped_column(
        ForeignKey("natal_data.id", ondelete="RESTRICT"), nullable=True
    )
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id"), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    yookassa_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    refund_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    refund_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    report_delivery_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="orders")
    natal_data = relationship("NatalData", backref="orders")
    tariff = relationship("Tariff", backref="orders")
    report = relationship("Report", back_populates="order", uselist=False)
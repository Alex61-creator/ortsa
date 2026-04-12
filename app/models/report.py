from sqlalchemy import String, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.db.base import Base
import enum

class ReportStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    FAILED = "failed"

class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    chart_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    llm_response_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[ReportStatus] = mapped_column(SQLEnum(ReportStatus), default=ReportStatus.ACTIVE, nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    order = relationship("Order", back_populates="report")
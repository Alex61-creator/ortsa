from sqlalchemy import Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class OrderNatalItem(Base):
    """Дополнительные натальные профили для тарифа bundle (до 3 штук).

    Для одиночных тарифов (free/report/sub_*) используется Order.natal_data_id.
    Для bundle: primary в Order.natal_data_id, остальные (slot_index 2, 3) здесь.
    """
    __tablename__ = "order_natal_items"
    __table_args__ = (
        Index("ix_order_natal_items_order_id", "order_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    natal_data_id: Mapped[int] = mapped_column(
        ForeignKey("natal_data.id", ondelete="RESTRICT"), nullable=False
    )
    slot_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    natal_data = relationship("NatalData")

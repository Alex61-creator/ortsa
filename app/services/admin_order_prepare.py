"""Приведение заказа к состоянию, допустимому для постановки generate_report_task из админки."""

from fastapi import HTTPException, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.models.report import Report


async def prepare_order_for_admin_report_retry(db: AsyncSession, order: Order) -> None:
    if order.status in (
        OrderStatus.PENDING,
        OrderStatus.FAILED_TO_INIT_PAYMENT,
        OrderStatus.CANCELED,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Заказ не оплачен или отменён — перезапуск отчёта недоступен",
        )
    if order.status == OrderStatus.REFUNDED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Заказ с возвратом — перезапуск отчёта недоступен",
        )

    if order.status == OrderStatus.COMPLETED:
        await db.execute(delete(Report).where(Report.order_id == order.id))
        order.status = OrderStatus.PAID
    elif order.status == OrderStatus.FAILED:
        order.status = OrderStatus.PAID

    await db.commit()
    await db.refresh(order)

from fastapi import APIRouter

from . import dashboard, orders, reports, tariffs, users

router = APIRouter()
router.include_router(dashboard.router, prefix="/dashboard")
router.include_router(tariffs.router, prefix="/tariffs")
router.include_router(orders.router, prefix="/orders")
router.include_router(reports.router, prefix="/reports")
router.include_router(users.router, prefix="/users")

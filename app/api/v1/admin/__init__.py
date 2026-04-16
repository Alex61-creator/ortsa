from fastapi import APIRouter

from . import dashboard, export, flags, funnel, health, logs, metrics, orders, payments, promos, prompts, reports, settings, support, tariffs, tasks, users


router = APIRouter()
router.include_router(dashboard.router, prefix="/dashboard")
router.include_router(tariffs.router, prefix="/tariffs")
router.include_router(orders.router, prefix="/orders")
router.include_router(reports.router, prefix="/reports")
router.include_router(users.router, prefix="/users")
router.include_router(funnel.router, prefix="/funnel")
router.include_router(payments.router, prefix="/payments")
router.include_router(tasks.router, prefix="/tasks")
router.include_router(promos.router, prefix="/promos")
router.include_router(prompts.router, prefix="/prompts")
router.include_router(flags.router, prefix="/flags")
router.include_router(health.router, prefix="/health")
router.include_router(logs.router, prefix="/logs")
router.include_router(metrics.router, prefix="/metrics")
router.include_router(export.router, prefix="/export")
router.include_router(support.router, prefix="/support")
router.include_router(settings.router, prefix="/settings")


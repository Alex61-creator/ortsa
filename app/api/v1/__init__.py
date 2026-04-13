from fastapi import APIRouter

from . import admin, auth, geocode, natal_data, ops, orders, reports, subscriptions, system, tariffs, users, webhooks

api_router = APIRouter()

api_router.include_router(admin.router, prefix="/admin", tags=["Админка"])
api_router.include_router(system.router, prefix="/system", tags=["Служебное"])
api_router.include_router(auth.router, prefix="/auth", tags=["Авторизация"])
api_router.include_router(natal_data.router, prefix="/natal-data", tags=["Натальные данные"])
api_router.include_router(orders.router, prefix="/orders", tags=["Заказы"])
api_router.include_router(tariffs.router, prefix="/tariffs", tags=["Тарифы"])
api_router.include_router(reports.router, prefix="/reports", tags=["Отчёты"])
api_router.include_router(users.router, prefix="/users", tags=["Профиль и экспорт"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Вебхуки"])
api_router.include_router(geocode.router, prefix="/geocode", tags=["Геокодинг"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["Подписки"])
api_router.include_router(ops.router, prefix="/ops", tags=["Операции"])
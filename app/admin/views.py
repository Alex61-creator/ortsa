from sqladmin import ModelView, action
from starlette.requests import Request
from starlette.responses import StreamingResponse
import csv
import io
from sqlalchemy import select

from app.models.user import User
from app.models.order import Order
from app.models.report import Report
from app.models.tariff import Tariff
from app.models.natal_data import NatalData
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.refund import RefundService
from app.services.tariff import TariffService


class UserAdmin(ModelView, model=User):
    """Зарегистрированные пользователи: вход через OAuth/Telegram, флаг админа."""

    name = "Пользователь"
    name_plural = "Пользователи"
    category = "Пользователи"
    column_list = [User.id, User.email, User.oauth_provider, User.is_admin, User.created_at]
    column_searchable_list = [User.email]
    column_filters = [User.oauth_provider, User.is_admin]
    column_labels = {
        User.id: "ID",
        User.email: "Email",
        User.external_id: "Внешний ID",
        User.oauth_provider: "Способ входа",
        User.is_admin: "Администратор",
        User.consent_given_at: "Согласие (дата)",
        User.privacy_policy_version: "Версия политики",
        User.created_at: "Создан",
        User.updated_at: "Обновлён",
    }


class OrderAdmin(ModelView, model=Order):
    """Заказы на расчёт: тариф, ЮKassa, статус, возвраты и выгрузка в CSV."""

    name = "Заказ"
    name_plural = "Заказы"
    category = "Заказы и оплата"
    column_list = [Order.id, Order.user, Order.natal_data_id, Order.tariff, Order.status, Order.amount, Order.created_at]
    column_searchable_list = [Order.yookassa_id, Order.refund_id]
    column_filters = [Order.status]
    can_edit = True
    can_delete = False
    can_create = False
    column_labels = {
        Order.id: "ID",
        Order.user_id: "ID пользователя",
        Order.user: "Пользователь",
        Order.natal_data_id: "Натальные данные",
        Order.tariff_id: "ID тарифа",
        Order.tariff: "Тариф",
        Order.status: "Статус",
        Order.yookassa_id: "Платёж ЮKassa",
        Order.amount: "Сумма",
        Order.refund_id: "Возврат (ID)",
        Order.refunded_amount: "Сумма возврата",
        Order.refund_status: "Статус возврата",
        Order.celery_task_id: "Задача Celery",
        Order.created_at: "Создан",
        Order.updated_at: "Обновлён",
    }

    @action(
        name="refund_order",
        label="Создать возврат",
        confirmation_message="Инициировать возврат по выбранным заказам?",
    )
    async def refund_order(self, request: Request, pks: list):
        async with AsyncSession(request.app.state.engine) as session:
            service = RefundService()
            for pk in pks:
                await service.create_refund(session, int(pk))
        return {"message": f"Возврат инициирован для заказов: {pks}"}

    @action(name="export_csv", label="Экспорт в CSV")
    async def export_orders_csv(self, request: Request, pks: list):
        async with AsyncSession(request.app.state.engine) as session:
            stmt = select(Order).where(Order.id.in_(pks))
            result = await session.execute(stmt)
            orders = result.scalars().all()
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                [
                    "ID",
                    "ID пользователя",
                    "Тариф (код)",
                    "Статус",
                    "Сумма",
                    "Создан",
                ]
            )
            for order in orders:
                writer.writerow(
                    [
                        order.id,
                        order.user_id,
                        order.tariff.code if order.tariff else "",
                        order.status.value,
                        str(order.amount),
                        order.created_at.isoformat(),
                    ]
                )
            output.seek(0)
            return StreamingResponse(
                output,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=orders.csv"},
            )


class ReportAdmin(ModelView, model=Report):
    """Сгенерированные отчёты: PDF, статус, привязка к заказу."""

    name = "Отчёт"
    name_plural = "Отчёты"
    category = "Отчёты"
    column_list = [Report.id, Report.order, Report.status, Report.generated_at]
    column_filters = [Report.status]
    column_labels = {
        Report.id: "ID",
        Report.order_id: "ID заказа",
        Report.order: "Заказ",
        Report.pdf_path: "Путь к PDF",
        Report.chart_path: "Путь к карте",
        Report.llm_response_hash: "Хеш ответа LLM",
        Report.prompt_version: "Версия промпта",
        Report.status: "Статус",
        Report.generated_at: "Сгенерирован",
        Report.created_at: "Создан",
    }


class TariffAdmin(ModelView, model=Tariff):
    """Тарифные планы: цена, срок хранения, набор опций (JSON)."""

    name = "Тариф"
    name_plural = "Тарифы"
    category = "Тарифы"
    column_list = [
        Tariff.id,
        Tariff.code,
        Tariff.name,
        Tariff.llm_tier,
        Tariff.price,
        Tariff.price_usd,
        Tariff.compare_price_usd,
        Tariff.annual_total_usd,
        Tariff.billing_type,
        Tariff.subscription_interval,
        Tariff.retention_days,
    ]
    can_edit = True
    can_create = True
    can_delete = False
    column_labels = {
        Tariff.id: "ID",
        Tariff.code: "Код",
        Tariff.name: "Название",
        Tariff.llm_tier: "Уровень LLM (free / natal_full / pro)",
        Tariff.price: "Цена (₽, оплата)",
        Tariff.price_usd: "Цена отображения ($)",
        Tariff.compare_price_usd: "Старая цена $ (bundle)",
        Tariff.annual_total_usd: "Год в $ (Pro)",
        Tariff.features: "Опции (JSON), ключ max_natal_profiles",
        Tariff.retention_days: "Хранение, дней",
        Tariff.priority: "Приоритет",
        Tariff.billing_type: "Тип оплаты (one_time / subscription)",
        Tariff.subscription_interval: "Интервал подписки (month / year)",
    }

    async def after_model_change(self, data: dict, model: Tariff, is_created: bool, request: Request) -> None:
        await TariffService.invalidate_cache()


class NatalDataAdmin(ModelView, model=NatalData):
    """Введённые пользователем данные для расчёта: дата, место, координаты, дома."""

    name = "Натальные данные"
    name_plural = "Натальные данные"
    category = "Натальные данные"
    column_list = [NatalData.id, NatalData.user, NatalData.full_name, NatalData.birth_date, NatalData.created_at]
    column_searchable_list = [NatalData.full_name]
    can_delete = True
    column_labels = {
        NatalData.id: "ID",
        NatalData.user_id: "ID пользователя",
        NatalData.user: "Пользователь",
        NatalData.full_name: "ФИО",
        NatalData.birth_date: "Дата рождения",
        NatalData.birth_time: "Время рождения",
        NatalData.birth_place: "Место рождения",
        NatalData.lat: "Широта",
        NatalData.lon: "Долгота",
        NatalData.timezone: "Часовой пояс",
        NatalData.house_system: "Система домов",
        NatalData.created_at: "Создано",
    }

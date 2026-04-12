from fastapi import FastAPI
from sqladmin import Admin
from app.admin.auth import AdminAuth
from app.admin.views import UserAdmin, OrderAdmin, ReportAdmin, TariffAdmin, NatalDataAdmin
from app.core.config import settings
from app.db.session import engine

def setup_admin(app: FastAPI):
    authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
    admin = Admin(
        app,
        engine,
        title="Панель AstroGen",
        authentication_backend=authentication_backend,
    )
    admin.add_view(UserAdmin)
    admin.add_view(OrderAdmin)
    admin.add_view(ReportAdmin)
    admin.add_view(TariffAdmin)
    admin.add_view(NatalDataAdmin)
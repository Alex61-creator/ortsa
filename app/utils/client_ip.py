"""Определение IP клиента за reverse-proxy (Caddy, nginx)."""

from fastapi import Request


def get_client_ip(request: Request) -> str:
    """
    Первый адрес в X-Forwarded-For — исходный клиент при типичной цепочке
    «клиент → прокси → приложение». Если заголовка нет — peer сокета.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""

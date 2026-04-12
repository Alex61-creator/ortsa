"""
Заголовки безопасности: CSP только для HTML (лендинг с inline-скриптами и Telegram WebApp).
API JSON не получает строгий CSP.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Прагматичная политика: onclick/inline на лендинге, Telegram script, Google Fonts.
CSP_HTML = (
    "default-src 'self'; "
    "script-src 'self' https://telegram.org https://fonts.googleapis.com 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: https: blob:; "
    "connect-src 'self' https: wss:; "
    "frame-ancestors 'none'; "
    "base-uri 'self'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        ct = response.headers.get("content-type", "")
        if "text/html" in ct:
            response.headers.setdefault("Content-Security-Policy", CSP_HTML)
        return response

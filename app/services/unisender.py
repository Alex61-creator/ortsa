"""
Клиент Unisender Transactional Email API (sendEmail).
Документация: https://www.unisender.com/ru/support/api/partners/sendEmail/
"""
import base64
from pathlib import Path
from typing import Optional

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

UNISENDER_API_URL = "https://api.unisender.com/ru/api/sendEmail"


class UnisenderEmailService:
    """Отправка одиночных транзакционных писем через Unisender API."""

    def __init__(self) -> None:
        self._api_key = settings.UNISENDER_API_KEY

    async def send_email(
        self,
        *,
        to: str,
        subject: str,
        html_body: str,
        sender_name: str = "Astrogen",
        sender_email: Optional[str] = None,
        attachment_path: Optional[Path] = None,
        attachment_filename: Optional[str] = None,
    ) -> str:
        """
        Отправляет письмо через Unisender sendEmail.

        Returns:
            email_id из ответа Unisender.

        Raises:
            RuntimeError: если Unisender вернул ошибку.
        """
        from_email = sender_email or settings.SMTP_FROM

        params: dict = {
            "api_key": self._api_key,
            "format": "json",
            "email": to,
            "sender_name": sender_name,
            "sender_email": str(from_email),
            "subject": subject,
            "body": html_body,
        }

        # Вложение — PDF отчёт
        if attachment_path and attachment_path.exists():
            fname = attachment_filename or attachment_path.name
            raw = attachment_path.read_bytes()
            encoded = base64.b64encode(raw).decode("ascii")
            params[f"attachments[{fname}]"] = encoded

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(UNISENDER_API_URL, data=params)
            response.raise_for_status()
            result = response.json()

        if "error" in result:
            logger.error(
                "Unisender sendEmail error",
                error=result.get("error"),
                code=result.get("code"),
                email=to,
            )
            raise RuntimeError(f"Unisender error [{result.get('code')}]: {result.get('error')}")

        email_id = result.get("result", {}).get("id", "unknown")
        logger.info("Unisender email sent", email_id=email_id, to=to, subject=subject)
        return email_id

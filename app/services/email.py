"""
EmailService — отправка писем.

Если задан UNISENDER_API_KEY — использует Unisender Transactional API.
Иначе — fallback на fastapi-mail (SMTP/Mailhog для локальной разработки).
"""
from pathlib import Path
from typing import List, Optional

import structlog

from app.core.config import settings
from app.utils.sanitize import sanitize_email_subject

logger = structlog.get_logger(__name__)


class EmailService:
    async def send_email(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        template_name: Optional[str] = None,
        template_body: Optional[dict] = None,
        attachments: Optional[List[Path]] = None,
    ) -> None:
        subject = sanitize_email_subject(subject)

        if settings.UNISENDER_API_KEY:
            await self._send_via_unisender(
                recipients=recipients,
                subject=subject,
                template_name=template_name,
                template_body=template_body,
                attachments=attachments,
            )
        else:
            await self._send_via_smtp(
                recipients=recipients,
                subject=subject,
                body=body,
                template_name=template_name,
                template_body=template_body,
                attachments=attachments,
            )

    async def _send_via_unisender(
        self,
        recipients: List[str],
        subject: str,
        template_name: Optional[str],
        template_body: Optional[dict],
        attachments: Optional[List[Path]],
    ) -> None:
        from app.services.unisender import UnisenderEmailService

        html = self._render_template(template_name, template_body) if template_name else ""
        service = UnisenderEmailService()

        for to in recipients:
            attachment_path = attachments[0] if attachments else None
            try:
                await service.send_email(
                    to=to,
                    subject=subject,
                    html_body=html,
                    attachment_path=attachment_path,
                )
            except Exception as exc:
                logger.error(
                    "Unisender send failed",
                    to=to,
                    subject=subject,
                    error=str(exc),
                )
                raise

    async def _send_via_smtp(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        template_name: Optional[str],
        template_body: Optional[dict],
        attachments: Optional[List[Path]],
    ) -> None:
        from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

        conf = ConnectionConfig(
            MAIL_USERNAME=settings.SMTP_USER,
            MAIL_PASSWORD=settings.SMTP_PASSWORD,
            MAIL_FROM=settings.SMTP_FROM,
            MAIL_PORT=settings.SMTP_PORT,
            MAIL_SERVER=settings.SMTP_HOST,
            MAIL_STARTTLS=settings.SMTP_TLS,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=bool(settings.SMTP_USER),
            VALIDATE_CERTS=True,
            TEMPLATE_FOLDER=Path(__file__).resolve().parent.parent / "templates" / "email",
        )
        fm = FastMail(conf)
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=body,
            subtype="html",
            attachments=attachments or [],
        )
        if template_name:
            message.template_body = template_body
        await fm.send_message(message, template_name=template_name)

    def _render_template(self, template_name: str, context: Optional[dict]) -> str:
        """Рендерит Jinja2-шаблон из templates/email/ в строку HTML."""
        from jinja2 import Environment, FileSystemLoader

        template_dir = Path(__file__).resolve().parent.parent / "templates" / "email"
        env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)
        try:
            tmpl = env.get_template(template_name)
            return tmpl.render(**(context or {}))
        except Exception as exc:
            logger.error("Email template render failed", template=template_name, error=str(exc))
            return f"<p>Ваш отчёт готов. Заказ #{(context or {}).get('order_id', '?')}</p>"

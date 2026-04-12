from pathlib import Path
from typing import List, Optional
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import structlog

from app.core.config import settings
from app.utils.sanitize import sanitize_email_subject

logger = structlog.get_logger(__name__)

_MAIL_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"

conf = ConnectionConfig(
    MAIL_USERNAME=settings.SMTP_USER,
    MAIL_PASSWORD=settings.SMTP_PASSWORD,
    MAIL_FROM=settings.SMTP_FROM,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_HOST,
    MAIL_STARTTLS=settings.SMTP_TLS,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=_MAIL_TEMPLATE_DIR,
)

fm = FastMail(conf)

class EmailService:
    async def send_email(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        template_name: Optional[str] = None,
        template_body: Optional[dict] = None,
        attachments: Optional[List[Path]] = None
    ) -> None:
        subject = sanitize_email_subject(subject)
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=body,
            subtype="html",
            attachments=attachments or []
        )
        if template_name:
            message.template_body = template_body

        await fm.send_message(message, template_name=template_name)
        logger.info("Email sent", recipients=recipients, subject=subject)
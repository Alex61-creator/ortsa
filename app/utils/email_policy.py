"""Правила для email аккаунта: плейсхолдеры OAuth/Telegram и доставка отчётов."""


def is_placeholder_account_email(email: str | None) -> bool:
    """
    True если email — внутренний плейсхолдер (Telegram, OAuth без почты у провайдера).
    Такие адреса нельзя использовать для ЮKassa receipt и SMTP без явного report_delivery_email.
    """
    if not email or not isinstance(email, str):
        return True
    e = email.strip().lower()
    if e.endswith("@telegram.local"):
        return True
    if ".local" in e and "@oauth." in e:
        return True
    return False


def resolve_receipt_and_report_email(
    user_email: str | None,
    report_delivery_email: str | None,
) -> str | None:
    """
    Email для чека ЮKassa и отчёта: приоритет явного report_delivery_email,
    иначе реальный user.email.
    """
    if report_delivery_email and str(report_delivery_email).strip():
        return str(report_delivery_email).strip()
    if user_email and not is_placeholder_account_email(user_email):
        return user_email.strip()
    return None

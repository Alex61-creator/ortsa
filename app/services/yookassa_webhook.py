"""
Разбор и идемпотентность HTTP-уведомлений ЮKassa (официальная модель SDK).
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from yookassa.domain.notification import WebhookNotificationFactory

logger = structlog.get_logger(__name__)


def parse_notification(body: bytes) -> dict[str, Any]:
    """Парсит JSON и валидирует структуру через WebhookNotificationFactory (SDK ЮKassa)."""
    data = json.loads(body)
    if not isinstance(data, dict):
        raise ValueError("Body must be a JSON object")
    try:
        WebhookNotificationFactory().create(data)
    except Exception as exc:
        raise ValueError(f"Invalid notification: {exc}") from exc
    return data


def notification_idempotency_key(event: dict[str, Any]) -> str:
    """Ключ для дедупликации: событие + id объекта (платёж / возврат)."""
    evt = event.get("event") or ""
    obj = event.get("object") or {}
    oid = obj.get("id") or ""
    return f"webhook:{evt}:{oid}"

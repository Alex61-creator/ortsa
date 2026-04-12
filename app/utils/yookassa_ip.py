"""
Сети отправителей HTTP-уведомлений ЮKassa (актуально на 2026).
https://yookassa.ru/developers/using-api/webhooks — раздел «IP authentication».
"""

from __future__ import annotations

import ipaddress
from functools import lru_cache

# IPv4 и IPv6 подсети из официальной документации ЮKassa
_RAW_NETWORKS = (
    "185.71.76.0/27",
    "185.71.77.0/27",
    "77.75.153.0/25",
    "77.75.154.128/25",
    "77.75.156.11/32",
    "77.75.156.35/32",
    "2a02:5180::/32",
)


@lru_cache
def _networks():
    return tuple(ipaddress.ip_network(s) for s in _RAW_NETWORKS)


def is_yookassa_notification_ip(ip_str: str) -> bool:
    if not ip_str:
        return False
    try:
        ip = ipaddress.ip_address(ip_str.strip())
    except ValueError:
        return False
    return any(ip in net for net in _networks())

"""Генератор ICS-файлов для транзитных событий.

Создаёт RFC 5545-совместимый ICS-календарь из списка TransitEvent.
Пользователь открывает файл → «Добавить все события» в Google/Apple/Outlook Calendar.

Зависимость: icalendar==5.0.14 (в requirements.txt).
При отсутствии библиотеки использует ручную генерацию ICS.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from app.services.transit import TransitEvent

logger = structlog.get_logger(__name__)

# Описания аспектов для description поля события
_ASPECT_DESC_RU: dict[str, str] = {
    "conjunction": "Соединение — слияние энергий планет. Усиленный акцент на затронутых темах.",
    "sextile": "Секстиль — гармоничный поток возможностей и лёгкое взаимодействие.",
    "square": "Квадрат — напряжение, требующее действия и преодоления препятствий.",
    "trine": "Тригон — удача, плавный поток, природный талант.",
    "opposition": "Оппозиция — баланс между противоположными силами; необходима интеграция.",
}

_ASPECT_DESC_EN: dict[str, str] = {
    "conjunction": "Conjunction — merging of planetary energies. Strong emphasis on the themes involved.",
    "sextile": "Sextile — harmonious flow of opportunities and easy interaction.",
    "square": "Square — tension requiring action and overcoming obstacles.",
    "trine": "Trine — luck, smooth flow, natural talent.",
    "opposition": "Opposition — balance between opposing forces; integration needed.",
}

_PLANET_RU: dict[str, str] = {
    "Sun": "Солнце", "Moon": "Луна", "Mercury": "Меркурий",
    "Venus": "Венера", "Mars": "Марс", "Jupiter": "Юпитер",
    "Saturn": "Сатурн", "Uranus": "Уран", "Neptune": "Нептун",
    "Pluto": "Плутон", "Chiron": "Хирон",
    "Ascendant": "Асцендент", "MC": "МС",
}

_ASPECT_RU: dict[str, str] = {
    "conjunction": "соединение", "sextile": "секстиль",
    "square": "квадрат", "trine": "тригон", "opposition": "оппозиция",
}

_ENERGY_EMOJI: dict[str, str] = {
    "good": "🟢", "hard": "🔴", "neutral": "🔵",
}


def _event_summary(event: "TransitEvent", locale: str = "ru") -> str:
    """Краткое название события для заголовка в календаре."""
    emoji = _ENERGY_EMOJI.get(event.energy, "")
    if locale == "en":
        return f"{emoji} {event.transiting_planet} {event.aspect} natal {event.natal_planet}"
    t_ru = _PLANET_RU.get(event.transiting_planet, event.transiting_planet)
    n_ru = _PLANET_RU.get(event.natal_planet, event.natal_planet)
    a_ru = _ASPECT_RU.get(event.aspect, event.aspect)
    return f"{emoji} {t_ru} {a_ru} {n_ru}"


def _event_description(event: "TransitEvent", locale: str = "ru") -> str:
    """Подробное описание для тела события."""
    desc_map = _ASPECT_DESC_EN if locale == "en" else _ASPECT_DESC_RU
    base = desc_map.get(event.aspect, "")
    orb_label = "Orb" if locale == "en" else "Орбис"
    return f"{base}\n{orb_label}: {event.orb:.1f}°"


def _format_date(d: date) -> str:
    """Формат даты для ICS: YYYYMMDD."""
    return d.strftime("%Y%m%d")


def _format_datetime_utc(dt: datetime) -> str:
    """Формат datetime UTC для ICS: YYYYMMDDTHHMMSSZ."""
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _escape_ics(text: str) -> str:
    """Экранирует спецсимволы ICS."""
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def generate_ics(
    events: "list[TransitEvent]",
    calendar_name: str = "Астрологический календарь",
    locale: str = "ru",
) -> bytes:
    """
    Генерирует ICS-файл из списка транзитных событий.

    Args:
        events: Список TransitEvent от TransitService.
        calendar_name: Название календаря.
        locale: Язык подписей событий (ru | en).

    Returns:
        bytes — содержимое .ics файла в кодировке UTF-8.
    """
    try:
        return _generate_with_icalendar(events, calendar_name, locale)
    except ImportError:
        logger.warning("icalendar_not_installed", fallback="manual_ics")
        return _generate_manual_ics(events, calendar_name, locale)


def _generate_with_icalendar(
    events: "list[TransitEvent]",
    calendar_name: str,
    locale: str,
) -> bytes:
    """Генерация через библиотеку icalendar."""
    from icalendar import Calendar, Event, vText

    cal = Calendar()
    cal.add("prodid", "-//Astro Pro//Natal Chart//RU")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", vText(calendar_name))
    cal.add("x-wr-timezone", "UTC")

    now_utc = datetime.now(tz=timezone.utc)

    for ev in events:
        ical_event = Event()
        ical_event.add("uid", str(uuid.uuid4()))
        ical_event.add("dtstart", ev.date)  # ALL_DAY event
        ical_event.add("dtend", ev.date)
        ical_event.add("summary", _event_summary(ev, locale))
        ical_event.add("description", _event_description(ev, locale))
        ical_event.add("dtstamp", now_utc)

        # Цветовое кодирование через x-apple-calendar-color (Apple) и categories
        if ev.energy == "good":
            ical_event.add("categories", ["Благоприятно" if locale == "ru" else "Favorable"])
            ical_event.add("x-apple-calendar-color", "#00B050")
        elif ev.energy == "hard":
            ical_event.add("categories", ["Напряжённо" if locale == "ru" else "Challenging"])
            ical_event.add("x-apple-calendar-color", "#FF0000")
        else:
            ical_event.add("categories", ["Нейтрально" if locale == "ru" else "Neutral"])
            ical_event.add("x-apple-calendar-color", "#0070C0")

        cal.add_component(ical_event)

    return cal.to_ical()


def _generate_manual_ics(
    events: "list[TransitEvent]",
    calendar_name: str,
    locale: str,
) -> bytes:
    """Ручная генерация ICS без внешних зависимостей (fallback)."""
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Astro Pro//Natal Chart//RU",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape_ics(calendar_name)}",
        "X-WR-TIMEZONE:UTC",
    ]

    now_utc = datetime.now(tz=timezone.utc)
    dtstamp = _format_datetime_utc(now_utc)

    for ev in events:
        dtstart = _format_date(ev.date)
        summary = _escape_ics(_event_summary(ev, locale))
        description = _escape_ics(_event_description(ev, locale))
        uid = str(uuid.uuid4())
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTART;VALUE=DATE:{dtstart}",
            f"DTEND;VALUE=DATE:{dtstart}",
            f"DTSTAMP:{dtstamp}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines).encode("utf-8")

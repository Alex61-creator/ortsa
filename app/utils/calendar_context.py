"""Утилиты для подготовки контекста транзитного календаря.

Группирует TransitEvent по дням, добавляет лунные фазы и ключевые даты.
Результат используется как контекст для Jinja2-шаблона transit_calendar.html
и для LLM-промта.
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.transit import TransitEvent

_MONTH_RU = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]

_WEEKDAY_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
_WEEKDAY_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

_ASPECT_RU = {
    "conjunction": "☌", "sextile": "✶", "square": "□",
    "trine": "△", "opposition": "☍",
}

_ENERGY_EMOJI = {"good": "🟢", "hard": "🔴", "neutral": "🔵"}


@dataclass
class CalendarDay:
    date: date
    weekday: int            # 0=Mon … 6=Sun
    transits: list["TransitEvent"] = field(default_factory=list)
    is_new_moon: bool = False
    is_full_moon: bool = False
    moon_phase_label: str = ""
    is_highlighted: bool = False    # выделить жирной рамкой

    @property
    def top_transits(self) -> list["TransitEvent"]:
        """Топ-2 транзита по орбису."""
        return sorted(self.transits, key=lambda e: e.orb)[:2]

    @property
    def energy(self) -> str:
        """Общая энергия дня по топ-транзитам."""
        tops = self.top_transits
        if not tops:
            return "neutral"
        energies = [t.energy for t in tops]
        if "hard" in energies:
            return "hard"
        if "good" in energies:
            return "good"
        return "neutral"


@dataclass
class CalendarWeek:
    days: list[CalendarDay | None]  # 7 элементов, None = вне месяца


@dataclass
class CalendarContext:
    year: int
    month: int
    month_name: str
    month_name_en: str
    weeks: list[CalendarWeek]
    highlighted_dates: list[dict]   # список {date, label, reason}
    transit_summary: list[dict]     # топ-5 транзитов месяца для LLM


def build_calendar_context(
    events: "list[TransitEvent]",
    year: int,
    month: int,
    locale: str = "ru",
) -> CalendarContext:
    """
    Строит CalendarContext из списка транзитов.

    Args:
        events: Список TransitEvent за указанный месяц.
        year: Год.
        month: Месяц (1–12).
        locale: Язык подписей.

    Returns:
        CalendarContext — готов для передачи в Jinja2-шаблон.
    """
    # Индексируем транзиты по дате
    by_date: dict[date, list[TransitEvent]] = defaultdict(list)
    for ev in events:
        by_date[ev.date].append(ev)

    # Строим сетку календаря
    cal = calendar.Calendar(firstweekday=0)  # Понедельник первый
    month_days = cal.monthdatescalendar(year, month)

    _, last_day_num = calendar.monthrange(year, month)

    weeks: list[CalendarWeek] = []
    for week_dates in month_days:
        week_days: list[CalendarDay | None] = []
        for d in week_dates:
            if d.month != month:
                week_days.append(None)
            else:
                transits = by_date.get(d, [])
                cal_day = CalendarDay(
                    date=d,
                    weekday=d.weekday(),
                    transits=transits,
                )
                week_days.append(cal_day)
        weeks.append(CalendarWeek(days=week_days))

    # Выделяем ключевые даты
    highlighted: list[dict] = []
    _mark_highlighted_dates(weeks, month, year, highlighted)

    # Топ-5 транзитов месяца (наименьший орбис среди медленных планет)
    SLOW = {"Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}
    slow_events = sorted(
        [e for e in events if e.transiting_planet in SLOW],
        key=lambda e: e.orb,
    )
    transit_summary = [
        {
            "date": str(e.date),
            "label": e.label_ru if locale == "ru" else e.label_en,
            "orb": e.orb,
            "energy": e.energy,
        }
        for e in slow_events[:5]
    ]

    month_name_ru = _MONTH_RU[month]
    import calendar as _cal_module
    month_name_en = _cal_module.month_name[month]

    return CalendarContext(
        year=year,
        month=month,
        month_name=month_name_ru if locale == "ru" else month_name_en,
        month_name_en=month_name_en,
        weeks=weeks,
        highlighted_dates=highlighted,
        transit_summary=transit_summary,
    )


def _mark_highlighted_dates(
    weeks: list[CalendarWeek],
    month: int,
    year: int,
    highlighted: list[dict],
) -> None:
    """Помечает ключевые даты: Новолуние, Полнолуние (приблизительно)."""
    # Простая аппроксимация лунных фаз через эпоху
    # Новолуние: ~29.53 дней цикл, опорная дата — известное новолуние
    new_moon_epoch = date(2000, 1, 6)   # известное новолуние
    lunar_cycle = 29.53058867

    first_day = date(year, month, 1)
    _, last_day_num = calendar.monthrange(year, month)
    last_day = date(year, month, last_day_num)

    current = first_day
    while current <= last_day:
        days_since = (current - new_moon_epoch).days
        phase = (days_since % lunar_cycle) / lunar_cycle  # 0.0–1.0

        phase_label = ""
        is_new = is_full = False
        if phase < 0.03 or phase > 0.97:
            phase_label = "🌑 Новолуние"
            is_new = True
        elif 0.48 <= phase <= 0.52:
            phase_label = "🌕 Полнолуние"
            is_full = True

        if phase_label:
            highlighted.append({
                "date": str(current),
                "label": phase_label,
                "reason": "lunar_phase",
            })
            # Помечаем CalendarDay
            for week in weeks:
                for day in week.days:
                    if day and day.date == current:
                        day.is_new_moon = is_new
                        day.is_full_moon = is_full
                        day.moon_phase_label = phase_label
                        day.is_highlighted = True

        current += timedelta(days=1)


def events_to_weekly_context(
    events: "list[TransitEvent]",
    week_start: date,
    locale: str = "ru",
) -> dict:
    """
    Готовит контекст для еженедельного email-дайджеста.

    Returns:
        dict {
            "week_start": "2026-01-05",
            "week_end": "2026-01-11",
            "best_day": {...},
            "caution_day": {...},
            "top_transits": [...],
        }
    """
    week_end = week_start + timedelta(days=6)

    by_date: dict[date, list[TransitEvent]] = defaultdict(list)
    for ev in events:
        by_date[ev.date].append(ev)

    # Лучший день (максимум good транзитов)
    best_day = None
    best_score = -1
    caution_day = None
    caution_score = -1

    for d, evs in by_date.items():
        good_count = sum(1 for e in evs if e.energy == "good")
        hard_count = sum(1 for e in evs if e.energy == "hard")
        if good_count > best_score:
            best_score = good_count
            best_day = d
        if hard_count > caution_score:
            caution_score = hard_count
            caution_day = d

    # Топ-5 транзитов за неделю
    top = sorted(events, key=lambda e: e.orb)[:5]

    def _format_day(d: date | None) -> dict | None:
        if d is None:
            return None
        wd = d.weekday()
        label = _WEEKDAY_RU[wd] if locale == "ru" else _WEEKDAY_EN[wd]
        return {"date": str(d), "weekday_label": label, "day": d.day}

    return {
        "week_start": str(week_start),
        "week_end": str(week_end),
        "best_day": _format_day(best_day),
        "caution_day": _format_day(caution_day),
        "top_transits": [
            {
                "label": t.label_ru if locale == "ru" else t.label_en,
                "date": str(t.date),
                "energy": t.energy,
                "energy_emoji": _ENERGY_EMOJI.get(t.energy, ""),
                "orb": t.orb,
            }
            for t in top
        ],
    }

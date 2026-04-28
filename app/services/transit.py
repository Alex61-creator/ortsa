"""Сервис расчёта планетарных транзитов к натальной карте.

Использует kerykeion 5.x API:
  - AstrologicalSubjectFactory.from_birth_data(...) для построения карты
  - AspectsFactory.synastry_aspects(transit, natal) для аспектов

Орбисы:
  - Быстрые планеты (Луна, Меркурий, Венера, Марс): ± 1°
  - Медленные планеты (Юпитер, Сатурн, Уран, Нептун, Плутон): ± 2°

Возвращает список TransitEvent за указанный период.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import structlog
from kerykeion import AspectsFactory, AstrologicalSubjectFactory

logger = structlog.get_logger(__name__)

# ── Конфигурация ────────────────────────────────────────────────────────────

FAST_PLANETS = {"Moon", "Mercury", "Venus", "Mars"}
SLOW_PLANETS = {"Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Chiron"}

FAST_ORB = 1.0  # градус
SLOW_ORB = 2.0  # градусов

SUPPORTED_ASPECTS = {"conjunction", "sextile", "square", "trine", "opposition"}

# Определяет «энергию» аспекта для цветовой маркировки в календаре
ENERGY_MAP: dict[str, dict[str, str]] = {
    # aspect_type → {planet → energy}
    "trine":       {"default": "good"},
    "sextile":     {"default": "good"},
    "conjunction": {"default": "neutral"},
    "square":      {"default": "hard"},
    "opposition":  {"default": "hard"},
}

# Благотворные транзиты Юпитера/Венеры смягчают напряжённый аспект
BENEFIC_PLANETS = {"Jupiter", "Venus"}
MALEFIC_PLANETS = {"Saturn", "Mars"}


def _classify_energy(aspect: str, transiting_planet: str) -> str:
    """Определяет энергию транзита: good | hard | neutral."""
    if aspect in ("trine", "sextile"):
        return "good"
    if aspect in ("square", "opposition"):
        if transiting_planet in MALEFIC_PLANETS:
            return "hard"
        if transiting_planet in BENEFIC_PLANETS:
            return "neutral"
        return "hard"
    # conjunction зависит от планеты
    if transiting_planet in BENEFIC_PLANETS:
        return "good"
    if transiting_planet in MALEFIC_PLANETS:
        return "hard"
    return "neutral"


@dataclass
class TransitEvent:
    date: date
    transiting_planet: str
    aspect: str                  # "trine", "square", etc.
    natal_planet: str
    orb: float
    energy: str                  # "good" | "hard" | "neutral"
    transiting_sign: str = ""
    natal_sign: str = ""

    @property
    def label_ru(self) -> str:
        aspect_ru = {
            "conjunction": "соединение",
            "sextile": "секстиль",
            "square": "квадрат",
            "trine": "тригон",
            "opposition": "оппозиция",
        }.get(self.aspect, self.aspect)
        planet_ru = _PLANET_RU.get(self.transiting_planet, self.transiting_planet)
        natal_ru = _PLANET_RU.get(self.natal_planet, self.natal_planet)
        return f"{planet_ru} {aspect_ru} {natal_ru}"

    @property
    def label_en(self) -> str:
        return f"{self.transiting_planet} {self.aspect} natal {self.natal_planet}"


_PLANET_RU: dict[str, str] = {
    "Sun": "Солнце",
    "Moon": "Луна",
    "Mercury": "Меркурий",
    "Venus": "Венера",
    "Mars": "Марс",
    "Jupiter": "Юпитер",
    "Saturn": "Сатурн",
    "Uranus": "Уран",
    "Neptune": "Нептун",
    "Pluto": "Плутон",
    "Chiron": "Хирон",
    "Mean_Node": "Сев. узел",
    "True_Node": "Сев. узел",
    "Ascendant": "Асцендент",
    "MC": "МС",
}

# Планеты, которые мы считаем как транзитирующие (без Луны по умолчанию – слишком быстрая)
TRANSIT_PLANETS = ("Sun", "Moon", "Mercury", "Venus", "Mars",
                   "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto")

# Натальные точки, к которым проверяем аспекты
NATAL_POINTS = ("Sun", "Moon", "Mercury", "Venus", "Mars",
                "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
                "Ascendant", "MC")


def _build_subject_sync(
    name: str,
    year: int, month: int, day: int,
    hour: int, minute: int,
    lat: float, lon: float,
    tz_str: str,
) -> Any:
    return AstrologicalSubjectFactory.from_birth_data(
        name=name,
        year=year, month=month, day=day,
        hour=hour, minute=minute,
        city="", nation="",
        lng=lon, lat=lat,
        tz_str=tz_str,
        zodiac_type="Tropical",
        houses_system_identifier="P",
        online=False,
    )


def _natal_subject_from_chart_data(natal_data: dict) -> Any:
    """
    Строит kerykeion Subject из словаря данных натальной карты.

    natal_data ожидает поля: birth_date, birth_time, lat, lon, tz_str
    (формат как в NatalData модели).
    """
    from datetime import datetime as _dt

    bd = natal_data.get("birth_date")
    bt = natal_data.get("birth_time")

    if isinstance(bd, str):
        bd = _dt.fromisoformat(bd).date()
    if isinstance(bt, str):
        bt = _dt.fromisoformat(bt).time()

    # Поддержка datetime-объектов
    if hasattr(bd, "year"):
        year, month, day = bd.year, bd.month, bd.day
    else:
        year, month, day = bd["year"], bd["month"], bd["day"]

    if hasattr(bt, "hour"):
        hour, minute = bt.hour, bt.minute
    else:
        hour, minute = bt["hour"], bt["minute"]

    return _build_subject_sync(
        name=natal_data.get("name", "Native"),
        year=year, month=month, day=day,
        hour=hour, minute=minute,
        lat=float(natal_data["lat"]),
        lon=float(natal_data["lon"]),
        tz_str=natal_data["tz_str"],
    )


def _calculate_transits_for_day(
    transit_date: date,
    natal_subject: Any,
) -> list[TransitEvent]:
    """Синхронно рассчитывает транзиты за конкретный день."""
    transit_subject = _build_subject_sync(
        name="Transit",
        year=transit_date.year,
        month=transit_date.month,
        day=transit_date.day,
        hour=12, minute=0,   # полдень UTC
        lat=float(natal_subject.lat),
        lon=float(natal_subject.lng),
        tz_str=str(natal_subject.tz_str),
    )

    try:
        aspects_model = AspectsFactory.synastry_aspects(transit_subject, natal_subject)
        aspects_raw = aspects_model.model_dump(mode="json").get("aspects", [])
    except Exception as exc:
        logger.warning("transit_aspects_error", date=str(transit_date), error=str(exc))
        return []

    events: list[TransitEvent] = []
    for asp in aspects_raw:
        t_planet = asp.get("p1_name", "")
        n_planet = asp.get("p2_name", "")
        aspect_type = asp.get("aspect", "")
        orb = abs(float(asp.get("orbit", 99)))

        # Фильтр по поддерживаемым аспектам
        if aspect_type not in SUPPORTED_ASPECTS:
            continue

        # Фильтр по орбису
        max_orb = SLOW_ORB if t_planet in SLOW_PLANETS else FAST_ORB
        if orb > max_orb:
            continue

        energy = _classify_energy(aspect_type, t_planet)

        events.append(TransitEvent(
            date=transit_date,
            transiting_planet=t_planet,
            aspect=aspect_type,
            natal_planet=n_planet,
            orb=round(orb, 2),
            energy=energy,
        ))

    # Сортируем по орбису — точнее первыми
    events.sort(key=lambda e: e.orb)
    return events


class TransitService:
    """Сервис расчёта транзитов к натальной карте."""

    async def calculate_transits(
        self,
        natal_data: dict,
        date_from: date,
        date_to: date,
    ) -> list[TransitEvent]:
        """
        Рассчитывает транзиты за период [date_from, date_to] включительно.

        Args:
            natal_data: Словарь с данными натальной карты (birth_date, birth_time,
                        lat, lon, tz_str).
            date_from: Начало периода.
            date_to: Конец периода (включительно).

        Returns:
            Список TransitEvent, отсортированный по дате, затем по орбису.
        """
        natal_subject = await asyncio.to_thread(_natal_subject_from_chart_data, natal_data)

        all_events: list[TransitEvent] = []
        current = date_from
        while current <= date_to:
            day_events = await asyncio.to_thread(
                _calculate_transits_for_day, current, natal_subject
            )
            all_events.extend(day_events)
            current += timedelta(days=1)

        all_events.sort(key=lambda e: (e.date, e.orb))
        logger.info(
            "transits_calculated",
            date_from=str(date_from),
            date_to=str(date_to),
            total=len(all_events),
        )
        return all_events

    async def calculate_month_transits(
        self,
        natal_data: dict,
        year: int,
        month: int,
    ) -> list[TransitEvent]:
        """Удобный метод: транзиты за конкретный месяц."""
        import calendar
        _, last_day = calendar.monthrange(year, month)
        return await self.calculate_transits(
            natal_data,
            date_from=date(year, month, 1),
            date_to=date(year, month, last_day),
        )

    async def get_week_highlights(
        self,
        natal_data: dict,
        week_start: date,
    ) -> list[TransitEvent]:
        """Транзиты на 7 дней начиная с week_start."""
        return await self.calculate_transits(
            natal_data,
            date_from=week_start,
            date_to=week_start + timedelta(days=6),
        )

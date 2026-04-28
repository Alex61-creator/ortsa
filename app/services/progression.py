"""Сервис вторичных прогрессий (Secondary Progressions).

Метод: 1 день после рождения = 1 год жизни.
Рассчитывает прогрессированные позиции планет на заданный год жизни.

Использует kerykeion 5.x API: AstrologicalSubjectFactory.from_birth_data().
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

import structlog
from kerykeion import AspectsFactory, AstrologicalSubjectFactory

logger = structlog.get_logger(__name__)

_PLANET_RU: dict[str, str] = {
    "Sun": "Солнце", "Moon": "Луна", "Mercury": "Меркурий",
    "Venus": "Венера", "Mars": "Марс", "Jupiter": "Юпитер",
    "Saturn": "Сатурн", "Uranus": "Уран", "Neptune": "Нептун",
    "Pluto": "Плутон", "Chiron": "Хирон",
    "Ascendant": "Асцендент", "MC": "МС",
}

_SIGN_RU: dict[str, str] = {
    "Ari": "Овен", "Tau": "Телец", "Gem": "Близнецы",
    "Can": "Рак", "Leo": "Лев", "Vir": "Дева",
    "Lib": "Весы", "Sco": "Скорпион", "Sag": "Стрелец",
    "Cap": "Козерог", "Aqu": "Водолей", "Pis": "Рыбы",
}


@dataclass
class ProgressedPlanet:
    name: str
    sign: str
    position: float          # позиция в знаке (0–29.9°)
    abs_pos: float           # абсолютная позиция (0–359.9°)
    house: str
    retrograde: bool = False

    @property
    def sign_ru(self) -> str:
        return _SIGN_RU.get(self.sign[:3], self.sign)

    @property
    def name_ru(self) -> str:
        return _PLANET_RU.get(self.name, self.name)

    @property
    def position_label(self) -> str:
        retro = " ℞" if self.retrograde else ""
        return f"{self.name_ru} {self.position:.1f}° {self.sign_ru}{retro}"


@dataclass
class ProgressedAspect:
    progressed_planet: str
    natal_planet: str
    aspect: str
    orb: float
    exact_date_approx: str = ""     # приблизительная дата точности

    @property
    def label_ru(self) -> str:
        aspect_ru = {
            "conjunction": "соединение", "sextile": "секстиль",
            "square": "квадрат", "trine": "тригон", "opposition": "оппозиция",
        }.get(self.aspect, self.aspect)
        p_ru = _PLANET_RU.get(self.progressed_planet, self.progressed_planet)
        n_ru = _PLANET_RU.get(self.natal_planet, self.natal_planet)
        return f"Прог. {p_ru} {aspect_ru} натальный {n_ru}"


@dataclass
class ProgressionResult:
    target_year: int                              # год жизни (возраст)
    progressed_date: date                         # дата, соответствующая году жизни
    planets: list[ProgressedPlanet] = field(default_factory=list)
    aspects_to_natal: list[ProgressedAspect] = field(default_factory=list)
    progressed_moon_sign: str = ""                # знак прогрессированной Луны
    progressed_moon_next_sign_date: str = ""      # когда Луна перейдёт в следующий знак

    def to_llm_context(self) -> dict:
        """Словарь для передачи в LLM."""
        return {
            "target_year": self.target_year,
            "progressed_date": str(self.progressed_date),
            "planets": [
                {
                    "name": p.name,
                    "sign": p.sign,
                    "position": round(p.position, 2),
                    "house": p.house,
                    "retrograde": p.retrograde,
                }
                for p in self.planets
            ],
            "aspects_to_natal": [
                {
                    "progressed_planet": a.progressed_planet,
                    "natal_planet": a.natal_planet,
                    "aspect": a.aspect,
                    "orb": round(a.orb, 2),
                }
                for a in self.aspects_to_natal
            ],
            "progressed_moon_sign": self.progressed_moon_sign,
        }


def _birth_datetime(natal_data: dict) -> datetime:
    """Извлекает дату и время рождения из словаря natal_data."""
    bd = natal_data.get("birth_date")
    bt = natal_data.get("birth_time")

    if isinstance(bd, str):
        from datetime import date as _date
        bd = datetime.fromisoformat(bd).date()
    if isinstance(bt, str):
        bt = datetime.fromisoformat(bt).time()

    if hasattr(bd, "year"):
        year, month, day = bd.year, bd.month, bd.day
    else:
        year, month, day = bd["year"], bd["month"], bd["day"]

    if hasattr(bt, "hour"):
        hour, minute = bt.hour, bt.minute
    else:
        hour, minute = bt["hour"], bt["minute"]

    return datetime(year, month, day, hour, minute)


def _build_subject(
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


def _extract_planets(subject: Any) -> list[ProgressedPlanet]:
    """Извлекает планеты из kerykeion 5.x subject."""
    planet_keys = (
        "sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn",
        "uranus", "neptune", "pluto", "chiron",
    )
    payload = subject.model_dump(mode="json") if hasattr(subject, "model_dump") else {}
    planets = []
    for key in planet_keys:
        if key not in payload:
            continue
        p = payload[key]
        planets.append(ProgressedPlanet(
            name=p.get("name", key.capitalize()),
            sign=p.get("sign", ""),
            position=float(p.get("position", 0)),
            abs_pos=float(p.get("abs_pos", 0)),
            house=str(p.get("house", "")),
            retrograde=bool(p.get("retrograde", False)),
        ))
    return planets


def _calculate_progressions_sync(
    natal_data: dict,
    target_age: int,
) -> ProgressionResult:
    """
    Синхронно рассчитывает вторичные прогрессии.

    target_age: возраст в годах (= сколько дней после рождения).
    """
    birth_dt = _birth_datetime(natal_data)
    lat = float(natal_data["lat"])
    lon = float(natal_data["lon"])
    tz_str = natal_data["tz_str"]

    # Прогрессированная дата = дата рождения + target_age дней
    progressed_dt = birth_dt + timedelta(days=target_age)
    prog_date = progressed_dt.date()

    # Строим прогрессированную карту
    prog_subject = _build_subject(
        name="Progressed",
        year=progressed_dt.year,
        month=progressed_dt.month,
        day=progressed_dt.day,
        hour=progressed_dt.hour,
        minute=progressed_dt.minute,
        lat=lat, lon=lon,
        tz_str=tz_str,
    )

    # Строим натальную карту
    natal_subject = _build_subject(
        name="Natal",
        year=birth_dt.year,
        month=birth_dt.month,
        day=birth_dt.day,
        hour=birth_dt.hour,
        minute=birth_dt.minute,
        lat=lat, lon=lon,
        tz_str=tz_str,
    )

    # Аспекты прогрессированных планет к натальным
    try:
        aspects_model = AspectsFactory.synastry_aspects(prog_subject, natal_subject)
        aspects_raw = aspects_model.model_dump(mode="json").get("aspects", [])
    except Exception as exc:
        logger.warning("progressions_aspects_error", error=str(exc))
        aspects_raw = []

    PROG_ASPECTS = {"conjunction", "sextile", "square", "trine", "opposition"}
    PROG_ORB = 1.5  # прогрессии — узкий орбис

    prog_aspects: list[ProgressedAspect] = []
    for asp in aspects_raw:
        aspect_type = asp.get("aspect", "")
        orb = abs(float(asp.get("orbit", 99)))
        if aspect_type not in PROG_ASPECTS:
            continue
        if orb > PROG_ORB:
            continue
        prog_aspects.append(ProgressedAspect(
            progressed_planet=asp.get("p1_name", ""),
            natal_planet=asp.get("p2_name", ""),
            aspect=aspect_type,
            orb=round(orb, 2),
        ))

    prog_aspects.sort(key=lambda a: a.orb)

    # Прогрессированные планеты
    planets = _extract_planets(prog_subject)

    # Знак прогрессированной Луны
    prog_moon_sign = ""
    for p in planets:
        if p.name == "Moon":
            prog_moon_sign = p.sign_ru
            break

    return ProgressionResult(
        target_year=target_age,
        progressed_date=prog_date,
        planets=planets,
        aspects_to_natal=prog_aspects,
        progressed_moon_sign=prog_moon_sign,
    )


class ProgressionService:
    """Сервис расчёта вторичных прогрессий."""

    async def calculate(
        self,
        natal_data: dict,
        target_age: int | None = None,
        target_year: int | None = None,
    ) -> ProgressionResult:
        """
        Рассчитывает вторичные прогрессии.

        Args:
            natal_data: Данные натальной карты (birth_date, birth_time, lat, lon, tz_str).
            target_age: Возраст в годах (приоритет).
            target_year: Абсолютный год (если не передан target_age).

        Returns:
            ProgressionResult с прогрессированными планетами и аспектами.
        """
        if target_age is None and target_year is not None:
            birth_dt = _birth_datetime(natal_data)
            target_age = target_year - birth_dt.year

        if target_age is None:
            from datetime import date as _date
            birth_dt = _birth_datetime(natal_data)
            target_age = _date.today().year - birth_dt.year

        result = await asyncio.to_thread(
            _calculate_progressions_sync, natal_data, target_age
        )
        logger.info(
            "progressions_calculated",
            target_age=target_age,
            aspects_count=len(result.aspects_to_natal),
        )
        return result

    async def calculate_quarterly(
        self,
        natal_data: dict,
        target_age: int,
    ) -> dict[str, ProgressionResult]:
        """
        Рассчитывает прогрессии для каждого квартала года жизни.

        Returns:
            {"Q1": ProgressionResult, "Q2": ..., "Q3": ..., "Q4": ...}
        """
        quarters = {
            "Q1": target_age,
            "Q2": target_age + 91 // 365,   # ~3 месяца в долях года
            "Q3": target_age + 182 // 365,
            "Q4": target_age + 273 // 365,
        }

        # Для вторичных прогрессий квартал ≈ 91 день
        birth_dt = _birth_datetime(natal_data)
        base_days = target_age  # возраст = количество прогрессированных дней

        results: dict[str, ProgressionResult] = {}
        for label, extra_days in [("Q1", 0), ("Q2", 91), ("Q3", 182), ("Q4", 273)]:
            result = await asyncio.to_thread(
                _calculate_progressions_sync, natal_data, base_days + extra_days
            )
            results[label] = result
        return results

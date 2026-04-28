"""Сервис расчёта транзитов и вторичных прогрессий.

Использует kerykeion.TransitsTimeRangeFactory + EphemerisDataFactory для
получения аспектов транзитных/прогрессивных планет к натальной карте.
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from kerykeion import (
    AstrologicalSubjectFactory,
    EphemerisDataFactory,
    TransitsTimeRangeFactory,
)
from pydantic import BaseModel

from app.constants.forecast import (
    DEFAULT_FORECAST_WINDOW_DAYS,
    DEFAULT_ORBS,
    FORECAST_CACHE_TTL,
    PRIORITY_PLANETS,
    SLOW_PLANETS,
    TRANSIT_GRID_HOURS,
)
from app.core.cache import cache

logger = structlog.get_logger(__name__)

FORECAST_CACHE_PREFIX = "forecast:v1"


# ── DTO ───────────────────────────────────────────────────────────────────────

class TransitEvent(BaseModel):
    date: str                    # ISO datetime строка точки сетки
    planet_transit: str          # транзитная планета ("Mars")
    planet_natal: str            # натальная планета ("Sun")
    aspect_type: str             # "conjunction", "trine", ...
    orb: float                   # значение орба в градусах
    aspect_movement: str         # "Applying" | "Separating"
    priority: int                # 1 (низкий) – 5 (высокий)


class ProgressionEvent(BaseModel):
    date: str                    # дата окна (ISO)
    planet_progressed: str       # прогрессивная планета
    planet_natal: str            # натальная планета
    aspect_type: str
    orb: float
    aspect_movement: str
    is_exact_in_window: bool     # orb < 1.0 — точное попадание
    is_background: bool          # медленная планета (Saturn, Uranus, Neptune, Pluto)


class ForecastContext(BaseModel):
    window_start: str            # ISO datetime
    window_end: str              # ISO datetime
    transits: list[TransitEvent]
    progressions: list[ProgressionEvent]
    exact_hits: list[dict]       # TransitEvent/ProgressionEvent с orb < 1.0
    background_themes: list[ProgressionEvent]
    metadata: dict

    def to_llm_text(self, locale: str = "ru") -> str:
        """Форматирует контекст в структурированный текст для LLM-промпта."""
        lines: list[str] = []

        if locale == "en":
            lines.append(f"=== FORECAST WINDOW: {self.window_start[:10]} – {self.window_end[:10]} ===")
            lines.append("")

            if self.exact_hits:
                lines.append("KEY DATES (exact aspect hits):")
                for hit in self.exact_hits:
                    date = hit.get("date", "")[:10]
                    p1 = hit.get("planet_transit") or hit.get("planet_progressed", "")
                    p2 = hit.get("planet_natal", "")
                    asp = hit.get("aspect_type", "")
                    orb = hit.get("orb", 0.0)
                    lines.append(f"  • {date}: {p1} {asp} {p2} (orb {orb:.1f}°)")
                lines.append("")

            if self.transits:
                lines.append("ACTIVE TRANSITS:")
                # группируем по паре планет, показываем уникальные активные аспекты
                seen: set[str] = set()
                for t in sorted(self.transits, key=lambda x: -x.priority):
                    key = f"{t.planet_transit}_{t.aspect_type}_{t.planet_natal}"
                    if key in seen:
                        continue
                    seen.add(key)
                    lines.append(
                        f"  {t.planet_transit} {t.aspect_type} natal {t.planet_natal}"
                        f" (orb {t.orb:.1f}°, {t.aspect_movement})"
                    )
                lines.append("")

            if self.progressions:
                lines.append("SECONDARY PROGRESSIONS:")
                seen_p: set[str] = set()
                for p in self.progressions:
                    key = f"{p.planet_progressed}_{p.aspect_type}_{p.planet_natal}"
                    if key in seen_p:
                        continue
                    seen_p.add(key)
                    tag = " [background]" if p.is_background else ""
                    lines.append(
                        f"  Progressed {p.planet_progressed} {p.aspect_type} natal {p.planet_natal}"
                        f" (orb {p.orb:.1f}°){tag}"
                    )
        else:
            lines.append(f"=== ПРОГНОЗ НА ПЕРИОД: {self.window_start[:10]} – {self.window_end[:10]} ===")
            lines.append("")

            if self.exact_hits:
                lines.append("КЛЮЧЕВЫЕ ДАТЫ (точные аспекты):")
                for hit in self.exact_hits:
                    date = hit.get("date", "")[:10]
                    p1 = hit.get("planet_transit") or hit.get("planet_progressed", "")
                    p2 = hit.get("planet_natal", "")
                    asp = hit.get("aspect_type", "")
                    orb = hit.get("orb", 0.0)
                    lines.append(f"  • {date}: {p1} {asp} {p2} (орбис {orb:.1f}°)")
                lines.append("")

            if self.transits:
                lines.append("АКТИВНЫЕ ТРАНЗИТЫ:")
                seen = set()
                for t in sorted(self.transits, key=lambda x: -x.priority):
                    key = f"{t.planet_transit}_{t.aspect_type}_{t.planet_natal}"
                    if key in seen:
                        continue
                    seen.add(key)
                    lines.append(
                        f"  {t.planet_transit} {t.aspect_type} натальный {t.planet_natal}"
                        f" (орбис {t.orb:.1f}°, {t.aspect_movement})"
                    )
                lines.append("")

            if self.progressions:
                lines.append("ВТОРИЧНЫЕ ПРОГРЕССИИ:")
                seen_p = set()
                for p in self.progressions:
                    key = f"{p.planet_progressed}_{p.aspect_type}_{p.planet_natal}"
                    if key in seen_p:
                        continue
                    seen_p.add(key)
                    tag = " [фон]" if p.is_background else ""
                    lines.append(
                        f"  Прогрессивный {p.planet_progressed} {p.aspect_type} натальный {p.planet_natal}"
                        f" (орбис {p.orb:.1f}°){tag}"
                    )

        return "\n".join(lines)


# ── Вспомогательные функции ───────────────────────────────────────────────────

def _aspect_priority(planet_transit: str, planet_natal: str) -> int:
    """Приоритет 1–5: оба в PRIORITY_PLANETS → 5, один → 3, ни один → 1."""
    t_prio = planet_transit in PRIORITY_PLANETS
    n_prio = planet_natal in PRIORITY_PLANETS
    if t_prio and n_prio:
        return 5
    if t_prio or n_prio:
        return 3
    return 1


def _make_forecast_cache_key(
    natal_hash: str,
    window_start: datetime,
    window_end: datetime,
    kind: str,
) -> str:
    raw = json.dumps(
        {
            "natal": natal_hash,
            "ws": window_start.isoformat(),
            "we": window_end.isoformat(),
            "kind": kind,
        },
        sort_keys=True,
    )
    return f"{FORECAST_CACHE_PREFIX}:{kind}:{hashlib.sha256(raw.encode()).hexdigest()}"


def _natal_hash(natal_data: Any) -> str:
    """SHA256 по ключевым полям натальных данных."""
    raw = json.dumps(
        {
            "bd": natal_data.birth_date.isoformat(),
            "bt": natal_data.birth_time.isoformat(),
            "lat": float(natal_data.lat),
            "lon": float(natal_data.lon),
            "tz": natal_data.timezone,
            "hs": getattr(natal_data, "house_system", "P"),
        },
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


# ── Основной сервис ───────────────────────────────────────────────────────────

class ForecastService:
    """Вычисляет транзиты и вторичные прогрессии для натальной карты."""

    async def calculate_transits_window(
        self,
        natal_data: Any,
        window_start: datetime,
        window_end: datetime,
    ) -> list[TransitEvent]:
        """
        Возвращает список транзитных аспектов в заданном окне.

        natal_data — экземпляр app.models.natal_data.NatalData.
        """
        nhash = _natal_hash(natal_data)
        cache_key = _make_forecast_cache_key(nhash, window_start, window_end, "transits")

        cached = await cache.get(cache_key)
        if cached is not None:
            logger.debug("Forecast transits cache hit", natal=nhash)
            return [TransitEvent(**e) for e in cached]

        events = await asyncio.to_thread(
            self._compute_transits_sync,
            natal_data,
            window_start,
            window_end,
        )

        await cache.set(cache_key, [e.model_dump() for e in events], ttl=FORECAST_CACHE_TTL)
        return events

    def _compute_transits_sync(
        self,
        natal_data: Any,
        window_start: datetime,
        window_end: datetime,
    ) -> list[TransitEvent]:
        """Синхронный расчёт транзитов (запускается в thread pool)."""
        from datetime import timezone as tz

        # Нормализуем window_start/end в UTC
        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=tz.utc)
        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=tz.utc)

        tz_str = getattr(natal_data, "timezone", "UTC") or "UTC"
        lat = float(natal_data.lat)
        lon = float(natal_data.lon)
        house_system = getattr(natal_data, "house_system", "P") or "P"

        # Строим натальный subject
        bd = natal_data.birth_date
        bt = natal_data.birth_time
        natal_subject = AstrologicalSubjectFactory.from_birth_data(
            name=getattr(natal_data, "full_name", "Native"),
            year=bd.year, month=bd.month, day=bd.day,
            hour=bt.hour, minute=bt.minute,
            city="", nation="",
            lng=lon, lat=lat,
            tz_str=tz_str,
            zodiac_type="Tropical",
            houses_system_identifier=house_system,
            online=False,
        )

        # Эфемериды с шагом TRANSIT_GRID_HOURS часов
        ephem_factory = EphemerisDataFactory(
            start_datetime=window_start,
            end_datetime=window_end,
            step_type="hours",
            step=TRANSIT_GRID_HOURS,
            lat=lat,
            lng=lon,
            tz_str="UTC",
        )
        ephem_points = ephem_factory.get_ephemeris_data_as_astrological_subjects()

        if not ephem_points:
            return []

        transit_factory = TransitsTimeRangeFactory(natal_subject, ephem_points)
        result = transit_factory.get_transit_moments()

        events: list[TransitEvent] = []
        for moment in result.transits:
            for asp in moment.aspects:
                # Фильтруем: p1 — транзитная, p2 — натальная
                orb_val = abs(float(asp.orbit))
                asp_type = str(asp.aspect).lower()
                limit = DEFAULT_ORBS.get(asp_type, 3.0)
                if orb_val > limit:
                    continue

                planet_transit = str(asp.p1_name)
                planet_natal = str(asp.p2_name)

                events.append(
                    TransitEvent(
                        date=str(moment.date),
                        planet_transit=planet_transit,
                        planet_natal=planet_natal,
                        aspect_type=asp_type,
                        orb=round(orb_val, 3),
                        aspect_movement=str(getattr(asp, "aspect_movement", "Unknown")),
                        priority=_aspect_priority(planet_transit, planet_natal),
                    )
                )

        return events

    async def calculate_secondary_progressions_window(
        self,
        natal_data: Any,
        window_start: datetime,
        window_end: datetime,
    ) -> list[ProgressionEvent]:
        """
        Вторичные прогрессии: 1 день после рождения = 1 год жизни.
        Для каждого дня окна вычисляем progressed_date и считаем аспекты к натальной карте.
        """
        nhash = _natal_hash(natal_data)
        cache_key = _make_forecast_cache_key(nhash, window_start, window_end, "progressions")

        cached = await cache.get(cache_key)
        if cached is not None:
            logger.debug("Forecast progressions cache hit", natal=nhash)
            return [ProgressionEvent(**e) for e in cached]

        events = await asyncio.to_thread(
            self._compute_progressions_sync,
            natal_data,
            window_start,
            window_end,
        )

        await cache.set(cache_key, [e.model_dump() for e in events], ttl=FORECAST_CACHE_TTL)
        return events

    def _compute_progressions_sync(
        self,
        natal_data: Any,
        window_start: datetime,
        window_end: datetime,
    ) -> list[ProgressionEvent]:
        """Синхронный расчёт вторичных прогрессий (в thread pool)."""
        from datetime import timezone as tz

        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=tz.utc)
        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=tz.utc)

        tz_str = getattr(natal_data, "timezone", "UTC") or "UTC"
        lat = float(natal_data.lat)
        lon = float(natal_data.lon)
        house_system = getattr(natal_data, "house_system", "P") or "P"

        bd = natal_data.birth_date
        bt = natal_data.birth_time
        birth_dt = datetime(
            bd.year, bd.month, bd.day,
            bt.hour, bt.minute,
            tzinfo=tz.utc,
        )

        # Натальный subject — эталон
        natal_subject = AstrologicalSubjectFactory.from_birth_data(
            name=getattr(natal_data, "full_name", "Native"),
            year=bd.year, month=bd.month, day=bd.day,
            hour=bt.hour, minute=bt.minute,
            city="", nation="",
            lng=lon, lat=lat,
            tz_str=tz_str,
            zodiac_type="Tropical",
            houses_system_identifier=house_system,
            online=False,
        )

        events: list[ProgressionEvent] = []

        # Итерируем по дням окна (прогрессии меняются медленно, 1 день/год)
        current = window_start
        while current <= window_end:
            days_lived = (current - birth_dt).days
            if days_lived <= 0:
                current += timedelta(days=1)
                continue

            # Прогрессивная дата: birth_date + days_lived дней
            # (1 день после рождения ≡ 1 год прожитой жизни)
            progressed_dt = birth_dt + timedelta(days=days_lived)

            try:
                progressed_subject = AstrologicalSubjectFactory.from_birth_data(
                    name="Progressed",
                    year=progressed_dt.year,
                    month=progressed_dt.month,
                    day=progressed_dt.day,
                    hour=progressed_dt.hour,
                    minute=progressed_dt.minute,
                    city="", nation="",
                    lng=lon, lat=lat,
                    tz_str="UTC",
                    zodiac_type="Tropical",
                    houses_system_identifier=house_system,
                    online=False,
                )
            except Exception as exc:
                logger.warning(
                    "Progression subject build failed",
                    date=current.isoformat(),
                    error=str(exc),
                )
                current += timedelta(days=1)
                continue

            # Аспекты прогрессивных планет к натальным
            try:
                from kerykeion import AspectsFactory
                aspects_model = AspectsFactory.dual_chart_aspects(
                    progressed_subject, natal_subject
                )
                aspects_list = aspects_model.model_dump(mode="json").get("aspects", [])
            except Exception as exc:
                logger.warning(
                    "Progression aspects calc failed",
                    date=current.isoformat(),
                    error=str(exc),
                )
                aspects_list = []

            for asp in aspects_list:
                orb_val = abs(float(asp.get("orbit", asp.get("orb", 99.0))))
                asp_type = str(asp.get("aspect", "")).lower()
                limit = DEFAULT_ORBS.get(asp_type, 3.0)
                if orb_val > limit:
                    continue

                planet_prog = str(asp.get("p1_name", ""))
                planet_natal = str(asp.get("p2_name", ""))

                events.append(
                    ProgressionEvent(
                        date=current.isoformat(),
                        planet_progressed=planet_prog,
                        planet_natal=planet_natal,
                        aspect_type=asp_type,
                        orb=round(orb_val, 3),
                        aspect_movement=str(asp.get("aspect_movement", "Unknown")),
                        is_exact_in_window=orb_val < 1.0,
                        is_background=planet_prog in SLOW_PLANETS,
                    )
                )

            current += timedelta(days=1)

        return events

    async def build_forecast_context(
        self,
        natal_data: Any,
        window_start: datetime,
        window_end: datetime,
        include_transits: bool = True,
        include_progressions: bool = True,
    ) -> ForecastContext:
        """Строит полный ForecastContext для передачи в LLM и PDF."""
        transits: list[TransitEvent] = []
        progressions: list[ProgressionEvent] = []

        tasks = []
        if include_transits:
            tasks.append(self.calculate_transits_window(natal_data, window_start, window_end))
        if include_progressions:
            tasks.append(
                self.calculate_secondary_progressions_window(natal_data, window_start, window_end)
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        idx = 0
        if include_transits:
            r = results[idx]
            idx += 1
            if isinstance(r, Exception):
                logger.error("Transits calculation failed", error=str(r))
            else:
                transits = r  # type: ignore[assignment]
        if include_progressions:
            r = results[idx]
            idx += 1
            if isinstance(r, Exception):
                logger.error("Progressions calculation failed", error=str(r))
            else:
                progressions = r  # type: ignore[assignment]

        # Exact hits: orb < 1.0 из транзитов и прогрессий
        exact_hits: list[dict] = []
        for t in transits:
            if t.orb < 1.0:
                exact_hits.append(t.model_dump())
        for p in progressions:
            if p.is_exact_in_window:
                exact_hits.append(p.model_dump())

        # Фоновые темы из прогрессий
        background_themes = [p for p in progressions if p.is_background]

        return ForecastContext(
            window_start=window_start.isoformat(),
            window_end=window_end.isoformat(),
            transits=transits,
            progressions=progressions,
            exact_hits=exact_hits,
            background_themes=background_themes,
            metadata={
                "transit_grid_hours": TRANSIT_GRID_HOURS,
                "default_orbs": DEFAULT_ORBS,
                "include_transits": include_transits,
                "include_progressions": include_progressions,
            },
        )

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Any, Dict

import structlog
from kerykeion import AstrologicalSubject, Report, SynastryAspects
from kerykeion.charts.kerykeion_chart_svg import KerykeionChartSVG
from kerykeion.utilities import get_available_astrological_points_list, get_houses_list
from zoneinfo import ZoneInfo

logger = structlog.get_logger(__name__)


def _point_to_dict(point: Any) -> dict:
    if hasattr(point, "model_dump"):
        return point.model_dump(mode="json")
    if isinstance(point, dict):
        return point
    return {"repr": str(point)}


class AstrologyService:
    async def calculate_chart(
        self,
        name: str,
        birth_date: datetime,
        birth_time: datetime,
        lat: float,
        lon: float,
        tz_str: str,
        house_system: str = "P",
    ) -> Dict[str, Any]:
        dt = datetime(
            birth_date.year,
            birth_date.month,
            birth_date.day,
            birth_time.hour,
            birth_time.minute,
            birth_time.second,
            tzinfo=ZoneInfo(tz_str),
        )

        def _build_subject() -> AstrologicalSubject:
            return AstrologicalSubject(
                name=name,
                year=dt.year,
                month=dt.month,
                day=dt.day,
                hour=dt.hour,
                minute=dt.minute,
                city="",
                nation="",
                lng=lon,
                lat=lat,
                tz_str=tz_str,
                zodiac_type="Tropic",
                houses_system_identifier=house_system,
                online=False,
            )

        subject = await asyncio.to_thread(_build_subject)
        report = Report(subject)
        report_data = await asyncio.to_thread(report.get_full_report)

        chart = KerykeionChartSVG(subject, chart_type="Natal")
        svg_content = await asyncio.to_thread(chart.makeTemplate)

        import cairosvg

        png_data = await asyncio.to_thread(cairosvg.svg2png, bytestring=svg_content.encode())

        planets = get_available_astrological_points_list(subject)
        houses = get_houses_list(subject)
        angle_attrs = ("asc", "dsc", "mc", "ic")
        angles = [_point_to_dict(getattr(subject, a)) for a in angle_attrs if hasattr(subject, a)]

        return {
            "report": report_data,
            "svg": svg_content,
            "png": png_data,
            "instance": {
                "planets": [_point_to_dict(p) for p in planets],
                "houses": [_point_to_dict(h) for h in houses],
                "angles": angles,
            },
        }

    async def calculate_synastry(
        self,
        person1: dict,
        person2: dict,
    ) -> Dict[str, Any]:
        """
        Рассчитывает синастрию между двумя персонами.

        person1/person2 — dict с полями:
            name, birth_date (datetime), birth_time (datetime),
            lat, lon, tz_str, house_system
        Возвращает dict:
            subject1, subject2 — данные по каждой карте (planets/houses/angles)
            aspects — список аспектов синастрии
            png — PNG двойного колеса (bytes)
        """

        def _build(p: dict) -> AstrologicalSubject:
            bd: datetime = p["birth_date"]
            bt: datetime = p["birth_time"]
            dt = datetime(
                bd.year, bd.month, bd.day,
                bt.hour, bt.minute, bt.second,
                tzinfo=ZoneInfo(p["tz_str"]),
            )
            return AstrologicalSubject(
                name=p["name"],
                year=dt.year,
                month=dt.month,
                day=dt.day,
                hour=dt.hour,
                minute=dt.minute,
                city="",
                nation="",
                lng=p["lon"],
                lat=p["lat"],
                tz_str=p["tz_str"],
                zodiac_type="Tropic",
                houses_system_identifier=p.get("house_system", "P"),
                online=False,
            )

        def _run_sync():
            s1 = _build(person1)
            s2 = _build(person2)

            # Двойное колесо
            chart = KerykeionChartSVG(s1, chart_type="Synastry", second_obj=s2)
            svg_content = chart.makeTemplate()

            import cairosvg
            png_data = cairosvg.svg2png(bytestring=svg_content.encode())

            # Аспекты синастрии
            synastry = SynastryAspects(s1, s2)
            all_aspects = synastry.get_all_aspects()

            # Нормализуем аспекты
            aspects_list = []
            if isinstance(all_aspects, dict):
                for planet_key, asp_list in all_aspects.items():
                    if isinstance(asp_list, list):
                        for asp in asp_list:
                            if hasattr(asp, "model_dump"):
                                aspects_list.append(asp.model_dump(mode="json"))
                            elif isinstance(asp, dict):
                                aspects_list.append(asp)
            elif isinstance(all_aspects, list):
                for asp in all_aspects:
                    if hasattr(asp, "model_dump"):
                        aspects_list.append(asp.model_dump(mode="json"))
                    elif isinstance(asp, dict):
                        aspects_list.append(asp)

            def _subject_data(s: AstrologicalSubject) -> dict:
                planets = get_available_astrological_points_list(s)
                houses = get_houses_list(s)
                angle_attrs = ("asc", "dsc", "mc", "ic")
                angles = [
                    _point_to_dict(getattr(s, a))
                    for a in angle_attrs if hasattr(s, a)
                ]
                return {
                    "planets": [_point_to_dict(p) for p in planets],
                    "houses": [_point_to_dict(h) for h in houses],
                    "angles": angles,
                }

            return {
                "png": png_data,
                "subject1": _subject_data(s1),
                "subject2": _subject_data(s2),
                "aspects": aspects_list,
            }

        return await asyncio.to_thread(_run_sync)

    def make_cache_key(self, *args, **kwargs) -> str:
        data = {
            "name": kwargs.get("name"),
            "birth_date": kwargs.get("birth_date").isoformat(),
            "birth_time": kwargs.get("birth_time").isoformat(),
            "lat": kwargs.get("lat"),
            "lon": kwargs.get("lon"),
            "tz": kwargs.get("tz_str"),
            "house_system": kwargs.get("house_system"),
        }
        raw = json.dumps(data, sort_keys=True)
        return f"astro:{hashlib.md5(raw.encode()).hexdigest()}"

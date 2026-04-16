import asyncio
import hashlib
import json
from datetime import datetime
from typing import Any, Dict

import structlog
from kerykeion import AspectsFactory, AstrologicalSubjectFactory, ChartDataFactory, ChartDrawer, to_context
from zoneinfo import ZoneInfo

logger = structlog.get_logger(__name__)


def _point_to_dict(point: Any) -> dict:
    if hasattr(point, "model_dump"):
        return point.model_dump(mode="json")
    if isinstance(point, dict):
        return point
    return {"repr": str(point)}


def _extract_subject_instance(subject: Any) -> dict[str, list[dict[str, Any]]]:
    payload = subject.model_dump(mode="json") if hasattr(subject, "model_dump") else {}

    planet_keys = (
        "sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn",
        "uranus", "neptune", "pluto", "mean_north_lunar_node", "true_north_lunar_node",
        "mean_south_lunar_node", "true_south_lunar_node", "chiron", "mean_lilith", "true_lilith",
    )
    house_keys = (
        "first_house", "second_house", "third_house", "fourth_house", "fifth_house", "sixth_house",
        "seventh_house", "eighth_house", "ninth_house", "tenth_house", "eleventh_house", "twelfth_house",
    )
    angle_keys = ("ascendant", "descendant", "medium_coeli", "imum_coeli")

    planets = [_point_to_dict(payload[k]) for k in planet_keys if k in payload]
    houses = [_point_to_dict(payload[k]) for k in house_keys if k in payload]
    angles = [_point_to_dict(payload[k]) for k in angle_keys if k in payload]
    return {"planets": planets, "houses": houses, "angles": angles}


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

        def _build_subject() -> Any:
            return AstrologicalSubjectFactory.from_birth_data(
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
                zodiac_type="Tropical",
                houses_system_identifier=house_system,
                online=False,
            )

        subject = await asyncio.to_thread(_build_subject)
        chart_data = await asyncio.to_thread(ChartDataFactory.create_natal_chart_data, subject)
        svg_content = await asyncio.to_thread(
            lambda: ChartDrawer(chart_data, chart_language="RU").generate_svg_string()
        )

        import cairosvg

        png_data = await asyncio.to_thread(cairosvg.svg2png, bytestring=svg_content.encode())
        report_data = chart_data.model_dump(mode="json")

        return {
            "report": report_data,
            "svg": svg_content,
            "png": png_data,
            "instance": _extract_subject_instance(subject),
            "llm_context": to_context(chart_data),
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

        def _build(p: dict) -> Any:
            bd: datetime = p["birth_date"]
            bt: datetime = p["birth_time"]
            dt = datetime(
                bd.year, bd.month, bd.day,
                bt.hour, bt.minute, bt.second,
                tzinfo=ZoneInfo(p["tz_str"]),
            )
            return AstrologicalSubjectFactory.from_birth_data(
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
                zodiac_type="Tropical",
                houses_system_identifier=p.get("house_system", "P"),
                online=False,
            )

        def _run_sync():
            s1 = _build(person1)
            s2 = _build(person2)

            chart_data = ChartDataFactory.create_synastry_chart_data(s1, s2)
            svg_content = ChartDrawer(chart_data, chart_language="RU").generate_svg_string()

            import cairosvg
            png_data = cairosvg.svg2png(bytestring=svg_content.encode())

            aspects_model = AspectsFactory.synastry_aspects(s1, s2)
            aspects_list = aspects_model.model_dump(mode="json").get("aspects", [])

            return {
                "png": png_data,
                "subject1": _extract_subject_instance(s1),
                "subject2": _extract_subject_instance(s2),
                "aspects": aspects_list,
                "chart_data": chart_data.model_dump(mode="json"),
                "llm_context": to_context(chart_data),
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
        return f"astro:{hashlib.sha256(raw.encode()).hexdigest()}"

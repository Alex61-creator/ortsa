from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kerykeion import AspectsFactory, AstrologicalSubjectFactory, ChartDataFactory, ChartDrawer, to_context

from app.services.astrology import _extract_subject_instance


def _json_dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


async def _run(output_dir: Path) -> None:
    s1 = AstrologicalSubjectFactory.from_birth_data(
        name="Baseline User",
        year=1992,
        month=5,
        day=24,
        hour=14,
        minute=35,
        lat=55.7558,
        lng=37.6173,
        tz_str="Europe/Moscow",
        houses_system_identifier="P",
        online=False,
    )
    s2 = AstrologicalSubjectFactory.from_birth_data(
        name="Partner User",
        year=1991,
        month=9,
        day=10,
        hour=8,
        minute=15,
        lat=59.9343,
        lng=30.3351,
        tz_str="Europe/Moscow",
        houses_system_identifier="P",
        online=False,
    )
    natal_chart = ChartDataFactory.create_natal_chart_data(s1)
    synastry_chart = ChartDataFactory.create_synastry_chart_data(s1, s2)
    natal_svg = ChartDrawer(natal_chart, chart_language="RU").generate_svg_string()
    synastry_svg = ChartDrawer(synastry_chart, chart_language="RU").generate_svg_string()
    synastry_aspects = AspectsFactory.synastry_aspects(s1, s2).model_dump(mode="json").get("aspects", [])

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "natal_wheel.svg").write_text(natal_svg, encoding="utf-8")
    (output_dir / "synastry_wheel.svg").write_text(synastry_svg, encoding="utf-8")

    try:
        import cairosvg

        (output_dir / "natal_wheel.png").write_bytes(cairosvg.svg2png(bytestring=natal_svg.encode()))
        (output_dir / "synastry_wheel.png").write_bytes(cairosvg.svg2png(bytestring=synastry_svg.encode()))
    except Exception:
        print("PNG generation skipped: cairosvg/cairo not available in current environment.")

    _json_dump(output_dir / "natal_instance.json", _extract_subject_instance(s1))
    _json_dump(output_dir / "natal_report.json", natal_chart.model_dump(mode="json"))
    _json_dump(output_dir / "natal_context.xml.json", {"context": to_context(natal_chart)})
    _json_dump(
        output_dir / "synastry_instance.json",
        {
            "subject1": _extract_subject_instance(s1),
            "subject2": _extract_subject_instance(s2),
            "aspects": synastry_aspects,
        },
    )
    _json_dump(output_dir / "synastry_chart_data.json", synastry_chart.model_dump(mode="json"))
    _json_dump(output_dir / "synastry_context.xml.json", {"context": to_context(synastry_chart)})

    print(f"Baseline generated at: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Kerykeion v5 baseline artifacts.")
    parser.add_argument(
        "--output-dir",
        default="tests/fixtures/kerykeion_baseline_v5",
        help="Directory for golden artifacts.",
    )
    args = parser.parse_args()
    asyncio.run(_run(Path(args.output_dir)))


if __name__ == "__main__":
    main()

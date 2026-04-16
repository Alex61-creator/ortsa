import asyncio
import re
from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# ── Jinja2 фильтры ─────────────────────────────────────────────────────────────

_PLANET_NAMES_RU: dict[str, str] = {
    "Sun": "Солнце", "Moon": "Луна", "Mercury": "Меркурий",
    "Venus": "Венера", "Mars": "Марс", "Jupiter": "Юпитер",
    "Saturn": "Сатурн", "Uranus": "Уран", "Neptune": "Нептун",
    "Pluto": "Плутон", "Chiron": "Хирон", "Lilith": "Лилит",
    "MeanNode": "Сев. узел", "TrueNode": "Сев. узел",
    "TrueSouthNode": "Юж. узел", "MeanSouthNode": "Юж. узел",
}

_SIGN_NAMES_RU: dict[str, str] = {
    "Aries": "Овен", "Taurus": "Телец", "Gemini": "Близнецы",
    "Cancer": "Рак", "Leo": "Лев", "Virgo": "Дева",
    "Libra": "Весы", "Scorpio": "Скорпион", "Sagittarius": "Стрелец",
    "Capricorn": "Козерог", "Aquarius": "Водолей", "Pisces": "Рыбы",
}

_ELEMENT_NAMES_RU: dict[str, str] = {
    "Fire": "Огонь", "Earth": "Земля", "Air": "Воздух", "Water": "Вода",
}

_HOUSE_ROMAN: dict[str, str] = {
    "First_House": "I", "Second_House": "II", "Third_House": "III",
    "Fourth_House": "IV", "Fifth_House": "V", "Sixth_House": "VI",
    "Seventh_House": "VII", "Eighth_House": "VIII", "Ninth_House": "IX",
    "Tenth_House": "X", "Eleventh_House": "XI", "Twelfth_House": "XII",
}


def _filter_planet_name_ru(name: str) -> str:
    return _PLANET_NAMES_RU.get(name, name)


def _filter_sign_name_ru(sign: str) -> str:
    return _SIGN_NAMES_RU.get(sign, sign)


def _filter_element_ru(element: str) -> str:
    return _ELEMENT_NAMES_RU.get(element, element)


def _filter_house_roman(house: str) -> str:
    if not house:
        return "—"
    return _HOUSE_ROMAN.get(house, house.replace("_House", "").replace("_", " "))


def _filter_md_to_html(text: str) -> str:
    """Конвертирует упрощённый Markdown (секции LLM) в HTML.
    Поддерживает: **жирный**, *курсив*, - список, параграфы.
    """
    if not text:
        return ""

    # Нормализуем переносы строк
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n{2,}", text.strip())
    result: list[str] = []

    for block in blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue

        # Проверяем — это блок списка?
        list_items = []
        non_list_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("- ") or stripped.startswith("* "):
                list_items.append(stripped[2:])
            else:
                non_list_lines.append(stripped)

        if list_items and not non_list_lines:
            html_items = []
            for item in list_items:
                item = _inline_markup(item)
                html_items.append(f"<li>{item}</li>")
            result.append("<ul>" + "".join(html_items) + "</ul>")
        else:
            # Обычный параграф — объединяем строки
            para = " ".join(l for l in lines if l.strip())
            para = _inline_markup(para)
            if para:
                result.append(f"<p>{para}</p>")

    return "".join(result)


def _inline_markup(text: str) -> str:
    """Inline: **bold**, *italic*."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+?)\*", r"<em>\1</em>", text)
    return text


class PDFGenerator:
    def __init__(self):
        template_dir = Path(__file__).parent.parent / "templates" / "pdf"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=False)
        # Регистрируем фильтры
        self.env.filters["planet_name_ru"] = _filter_planet_name_ru
        self.env.filters["sign_name_ru"] = _filter_sign_name_ru
        self.env.filters["element_ru"] = _filter_element_ru
        self.env.filters["house_roman"] = _filter_house_roman
        self.env.filters["md_to_html"] = _filter_md_to_html

    async def generate(
        self,
        template_name: str,
        context: Dict[str, Any],
        output_filename: str,
    ) -> Path:
        template = self.env.get_template(template_name)
        html_content = template.render(**context)

        output_path = settings.STORAGE_DIR / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        def _render():
            html = HTML(string=html_content)
            # Базовый CSS — минимум; вся стилизация внутри шаблона
            css = CSS(string="@page { size: A4; margin: 0; } * { box-sizing: border-box; }")
            html.write_pdf(output_path, stylesheets=[css])

        await asyncio.to_thread(_render)
        logger.info("PDF generated", path=str(output_path))
        return output_path

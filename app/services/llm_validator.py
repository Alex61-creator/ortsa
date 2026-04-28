"""
LLM Response Validator — структура + язык.

Логика:
1. validate_structure: проверяет, что ≥ 50% ожидаемых разделов присутствуют в ответе.
2. validate_language: проверяет долю кириллицы/латиницы в тексте.
3. validate_response: вызывает оба проверки, бросает LLMValidationError при несоответствии.
4. language_enforcement_suffix: возвращает строку для усиленной инструкции языка в промпте.
"""
from __future__ import annotations

import re

from app.constants.tariffs import LlmTier
from app.schemas.llm import LLMResponseSchema

# ── Исключение ────────────────────────────────────────────────────────────────

class LLMValidationError(Exception):
    """Ответ не прошёл валидацию структуры или языка."""


# ── Ожидаемые разделы по тиру и локали ───────────────────────────────────────

EXPECTED_SECTIONS_RU: dict[LlmTier, list[str]] = {
    LlmTier.FREE: [
        "ОБЩИЙ ОБЗОР",
        "СОЛНЦЕ",
        "ЛУНА",
        "АСЦЕНДЕНТ",
    ],
    LlmTier.NATAL_FULL: [
        "ОБЩАЯ ХАРАКТЕРИСТИКА",
        "СОЛНЦЕ",
        "ЛУНА",
        "МЕРКУРИЙ",
        "ВЕНЕРА",
        "МАРС",
        "ЮПИТЕР",
        "САТУРН",
        "ВЫСШИЕ ПЛАНЕТЫ",
        "АСЦЕНДЕНТ И ДОМА",
        "АСПЕКТЫ",
        "НОДАЛЬНАЯ ОСЬ И КАРМА",
        "РЕКОМЕНДАЦИИ",
    ],
    LlmTier.PRO: [
        "ОБЩАЯ ХАРАКТЕРИСТИКА",
        "СОЛНЦЕ",
        "ЛУНА",
        "МЕРКУРИЙ",
        "ВЕНЕРА",
        "МАРС",
        "ЮПИТЕР",
        "САТУРН",
        "ВЫСШИЕ ПЛАНЕТЫ",
        "АСЦЕНДЕНТ И ДОМА",
        "АСПЕКТЫ",
        "НОДАЛЬНАЯ ОСЬ И КАРМА",
        "РЕКОМЕНДАЦИИ",
        "ТРАНЗИТЫ НА МЕСЯЦ",
        "УГЛУБЛЁННЫЙ АНАЛИЗ",
    ],
}

EXPECTED_SECTIONS_EN: dict[LlmTier, list[str]] = {
    LlmTier.FREE: [
        "OVERVIEW",
        "SUN",
        "MOON",
        "ASCENDANT",
    ],
    LlmTier.NATAL_FULL: [
        "GENERAL OVERVIEW",
        "SUN",
        "MOON",
        "MERCURY",
        "VENUS",
        "MARS",
        "JUPITER",
        "SATURN",
        "OUTER PLANETS",
        "ASCENDANT & HOUSES",
        "ASPECTS",
        "NODAL AXIS & KARMA",
        "RECOMMENDATIONS",
    ],
    LlmTier.PRO: [
        "GENERAL OVERVIEW",
        "SUN",
        "MOON",
        "MERCURY",
        "VENUS",
        "MARS",
        "JUPITER",
        "SATURN",
        "OUTER PLANETS",
        "ASCENDANT & HOUSES",
        "ASPECTS",
        "NODAL AXIS & KARMA",
        "RECOMMENDATIONS",
        "TRANSITS FOR THE MONTH",
        "DEEP DIVE",
    ],
}

# Ожидаемые разделы синастрии
EXPECTED_SYNASTRY_SECTIONS_RU: list[str] = [
    "ОБЩАЯ СОВМЕСТНОСТЬ",
    "ЭМОЦИОНАЛЬНАЯ СВЯЗЬ",
    "ИНТЕЛЛЕКТУАЛЬНАЯ СОВМЕСТИМОСТЬ",
    "РОМАНТИКА И ПРИТЯЖЕНИЕ",
    "КОНФЛИКТЫ И ВЫЗОВЫ",
    "ДОЛГОСРОЧНЫЙ ПОТЕНЦИАЛ",
    "КЛЮЧЕВЫЕ АСПЕКТЫ СИНАСТРИИ",
    "РЕКОМЕНДАЦИИ ДЛЯ ПАРТНЁРОВ",
]

EXPECTED_SYNASTRY_SECTIONS_EN: list[str] = [
    "OVERALL COMPATIBILITY",
    "EMOTIONAL CONNECTION",
    "INTELLECTUAL COMPATIBILITY",
    "ROMANCE & ATTRACTION",
    "CONFLICTS & CHALLENGES",
    "LONG-TERM POTENTIAL",
    "KEY SYNASTRY ASPECTS",
    "RECOMMENDATIONS FOR PARTNERS",
]

# Минимальная доля совпавших разделов
_MIN_SECTION_RATIO = 0.5
# Минимальная доля кириллицы/латиницы в тексте
_MIN_LANGUAGE_RATIO = 0.30


# ── Вспомогательные функции ───────────────────────────────────────────────────

def _cyrillic_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    cyrillic = sum(1 for c in letters if "Ѐ" <= c <= "ӿ")
    return cyrillic / len(letters)


def _latin_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    latin = sum(1 for c in letters if c.isascii() and c.isalpha())
    return latin / len(letters)


def _sections_present(response: LLMResponseSchema, expected: list[str]) -> int:
    """Считает, сколько ожидаемых разделов есть в ответе (нечувствительно к регистру)."""
    raw_upper = response.raw_content.upper()
    section_keys_upper = {k.upper() for k in response.sections}
    count = 0
    for sec in expected:
        sec_upper = sec.upper()
        # Ищем по ключу sections или по сырому содержимому
        if sec_upper in section_keys_upper or re.search(rf"\[{re.escape(sec_upper)}\]", raw_upper):
            count += 1
    return count


# ── Публичный API ─────────────────────────────────────────────────────────────

def validate_structure(
    response: LLMResponseSchema,
    tier: LlmTier,
    locale: str,
    *,
    is_synastry: bool = False,
) -> None:
    """Проверяет, что ≥ 50% ожидаемых разделов присутствуют в ответе.

    Raises:
        LLMValidationError — если проверка не пройдена.
    """
    if is_synastry:
        expected = EXPECTED_SYNASTRY_SECTIONS_EN if locale == "en" else EXPECTED_SYNASTRY_SECTIONS_RU
    else:
        mapping = EXPECTED_SECTIONS_EN if locale == "en" else EXPECTED_SECTIONS_RU
        expected = mapping.get(tier, [])

    if not expected:
        return  # нечего проверять

    found = _sections_present(response, expected)
    ratio = found / len(expected)

    if ratio < _MIN_SECTION_RATIO:
        raise LLMValidationError(
            f"Validation failed: only {found}/{len(expected)} expected sections found "
            f"(ratio={ratio:.2f}, threshold={_MIN_SECTION_RATIO}). "
            f"Missing: {[s for s in expected if s.upper() not in {k.upper() for k in response.sections}]}"
        )


def validate_language(response: LLMResponseSchema, locale: str) -> None:
    """Проверяет, что текст написан на нужном языке.

    Raises:
        LLMValidationError — если проверка не пройдена.
    """
    text = response.raw_content
    if locale == "en":
        ratio = _latin_ratio(text)
        if ratio < _MIN_LANGUAGE_RATIO:
            raise LLMValidationError(
                f"Language validation failed: expected English (locale=en), "
                f"but Latin ratio={ratio:.2f} < {_MIN_LANGUAGE_RATIO}."
            )
    else:
        # ru и всё остальное — ожидаем кириллицу
        ratio = _cyrillic_ratio(text)
        if ratio < _MIN_LANGUAGE_RATIO:
            raise LLMValidationError(
                f"Language validation failed: expected Russian (locale={locale}), "
                f"but Cyrillic ratio={ratio:.2f} < {_MIN_LANGUAGE_RATIO}."
            )


def validate_response(
    response: LLMResponseSchema,
    tier: LlmTier,
    locale: str,
    *,
    is_synastry: bool = False,
) -> None:
    """Объединяет проверки структуры и языка.

    Raises:
        LLMValidationError — если любая проверка не пройдена.
    """
    validate_structure(response, tier, locale, is_synastry=is_synastry)
    validate_language(response, locale)


def language_enforcement_suffix(locale: str) -> str:
    """Возвращает строку-суффикс для усиленной инструкции языка в промпте."""
    if locale == "en":
        return "\n\nCRITICAL: You MUST respond ONLY in English. Any other language is unacceptable."
    return "\n\nВАЖНО: Ты ОБЯЗАН отвечать ТОЛЬКО на русском языке. Любой другой язык недопустим."

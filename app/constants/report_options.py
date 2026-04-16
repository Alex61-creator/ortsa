"""Канонические ключи доп. разделов отчёта (report / bundle) и тексты для UI / LLM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# Порядок в API и визарде
REPORT_OPTION_KEYS: Final[tuple[str, ...]] = (
    "partnership",
    "children_parenting",
    "career",
    "money_boundaries",
)

REPORT_OPTION_KEYS_SET: Final[frozenset[str]] = frozenset(REPORT_OPTION_KEYS)


@dataclass(frozen=True, slots=True)
class ReportOptionDefinition:
    key: str
    title: str
    description: str
    # Маркер секции в ответе LLM (как в существующих натальных промптах)
    section_marker: str


def report_option_definitions() -> tuple[ReportOptionDefinition, ...]:
    return (
        ReportOptionDefinition(
            key="partnership",
            title="Партнёрство",
            description=(
                "Как вы входите в близость, что для вас важно в паре и где чаще возникают "
                "типичные сценарии — по вашей карте, без данных партнёра."
            ),
            section_marker="## [ПАРТНЁРСТВО]",
        ),
        ReportOptionDefinition(
            key="children_parenting",
            title="Дети и родительская роль",
            description=(
                "Общие темы детей, ответственности и творческого взаимодействия с детьми "
                "в рамках вашей карты — без дат рождения детей."
            ),
            section_marker="## [ДЕТИ И РОДИТЕЛЬСКАЯ РОЛЬ]",
        ),
        ReportOptionDefinition(
            key="career",
            title="Карьера и реализация",
            description=(
                "Профессиональные роли, амбиции, нагрузка и направления развития навыков "
                "по натальной карте."
            ),
            section_marker="## [КАРЬЕРА И РЕАЛИЗАЦИЯ]",
        ),
        ReportOptionDefinition(
            key="money_boundaries",
            title="Деньги, границы, опора",
            description=(
                "Темы дохода, рисков, границ с людьми и внутренней опоры — практично и без "
                "обещаний «инвестиционных сигналов»."
            ),
            section_marker="## [ДЕНЬГИ ГРАНИЦЫ ОПОРА]",
        ),
    )


def definition_by_key() -> dict[str, ReportOptionDefinition]:
    return {d.key: d for d in report_option_definitions()}


def normalize_report_options(raw: dict[str, bool] | None) -> dict[str, bool]:
    """Только канонические ключи; значение True сохраняется, остальное отбрасывается."""
    if not raw:
        return {}
    out: dict[str, bool] = {}
    for k in REPORT_OPTION_KEYS:
        if raw.get(k) is True:
            out[k] = True
    return out


def build_report_options_prompt_addon(flags: dict[str, bool] | None) -> str:
    """Фрагмент для добавления к system prompt: требуемые секции по включённым флагам."""
    norm = normalize_report_options(flags)
    if not norm:
        return ""
    by_key = definition_by_key()
    lines: list[str] = [
        "\n\n--- Дополнительные платные разделы (обязательно включи каждый включённый раздел "
        "с указанным маркером; не дублируй уже покрытое в основной структуре натала):"
    ]
    for k in REPORT_OPTION_KEYS:
        if not norm.get(k):
            continue
        d = by_key[k]
        lines.append(
            f"- {d.section_marker}: {d.title}. Раскрой тему по данным карты; избегай общих фраз без привязки к планетам/домам."
        )
    return "\n".join(lines)

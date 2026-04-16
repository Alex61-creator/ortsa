# Kerykeion v5 Regression Pack

Статус: `archived`  
Дата архивации: `2026-04-16`  
Дата фиксации: `2026-04-16`

## Baseline artifacts

- Скрипт генерации baseline: `scripts/generate_kerykeion_baseline.py`
- Каталог golden-артефактов: `tests/fixtures/kerykeion_baseline_v5`
- Зафиксированные артефакты:
  - `natal_instance.json`
  - `natal_report.json`
  - `natal_context.xml.json`
  - `natal_wheel.svg`
  - `synastry_instance.json`
  - `synastry_chart_data.json`
  - `synastry_context.xml.json`
  - `synastry_wheel.svg`
  - `natal_wheel.png` и `synastry_wheel.png` (если в окружении установлен `cairo`)

## Smoke / regression checklist

- [x] Factory API v5 используется в `app/services/astrology.py` (`AstrologicalSubjectFactory`, `ChartDataFactory`, `ChartDrawer`, `AspectsFactory`).
- [x] Контракт `calculate_chart()` сохранен для downstream (`report`, `svg`, `png`, `instance`) и расширен `llm_context`.
- [x] Контракт `calculate_synastry()` сохранен (`png`, `subject1`, `subject2`, `aspects`) и расширен (`chart_data`, `llm_context`).
- [x] PDF/LLM пайплайны используют явные pydantic-схемы контракта (`app/schemas/astrology.py`).
- [x] Добавлен feature flag `LLM_USE_KERYKEION_CONTEXT` для постепенного включения XML-контекста `to_context`.

## Test scope

- Unit/contract:
  - `tests/test_astrology_service_v5_contract.py`
  - `tests/test_llm_context_prompts.py`
  - обновленные тесты `report_generation` c новым контрактом chart-result.
- Интеграционные:
  - существующие `tests/test_report_generation_guards_and_errors.py`
  - существующие `tests/test_report_generation_latency.py`

## Security/code-review notes

- Добавлена ранняя валидация результата астрологического ядра через pydantic-схемы перед LLM/PDF, чтобы исключить «тихие» ошибки контракта.
- Внедрен controlled rollout для `to_context` через флаг, чтобы снизить риск деградации качества генерации.
- Ошибки почтового шага в синастрии не откатывают успешно сгенерированный отчет (поведение сохранено и проверено).

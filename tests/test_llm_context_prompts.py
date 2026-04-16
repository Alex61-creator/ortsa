from app.services.llm import LLMService
from app.services.synastry_llm import build_synastry_user_prompt


def test_build_user_prompt_uses_kerykeion_context():
    service = LLMService()
    prompt = service.build_user_prompt(
        chart_data={"sun": "Aries"},
        include_transits=False,
        locale="ru",
        chart_context="<chart_analysis>...</chart_analysis>",
    )
    assert "Структурированный контекст Kerykeion" in prompt
    assert "<chart_analysis>" in prompt


def test_synastry_prompt_uses_kerykeion_context():
    prompt = build_synastry_user_prompt(
        person1_name="A",
        person2_name="B",
        chart_data={},
        locale="en",
        chart_context="<chart_analysis>...</chart_analysis>",
    )
    assert "Kerykeion structured context" in prompt
    assert "Synastry analysis for" in prompt

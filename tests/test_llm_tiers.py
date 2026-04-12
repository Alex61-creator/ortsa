import pytest

from app.constants.tariffs import LlmTier
from app.services.llm import LLMService


def test_build_system_prompt_free_ru():
    svc = LLMService()
    p = svc.build_system_prompt(LlmTier.FREE, "ru")
    assert "ОБЩИЙ ОБЗОР" in p
    assert "ТРАНЗИТЫ" not in p
    assert "МЕРКУРИЙ" not in p


def test_build_system_prompt_natal_full_ru():
    svc = LLMService()
    p = svc.build_system_prompt(LlmTier.NATAL_FULL, "ru")
    assert "МЕРКУРИЙ" in p
    assert "НОДАЛЬНАЯ ОСЬ" in p
    assert "ТРАНЗИТЫ НА МЕСЯЦ" not in p


def test_build_system_prompt_pro_ru():
    svc = LLMService()
    p = svc.build_system_prompt(LlmTier.PRO, "ru")
    assert "ТРАНЗИТЫ НА МЕСЯЦ" in p
    assert "УГЛУБЛЁННЫЙ АНАЛИЗ" in p


@pytest.mark.parametrize(
    "tier,include",
    [
        (LlmTier.FREE, False),
        (LlmTier.NATAL_FULL, False),
        (LlmTier.PRO, True),
    ],
)
def test_build_user_prompt_transits_flag(tier, include):
    svc = LLMService()
    chart = {"test": 1}
    up = svc.build_user_prompt(chart, include_transits=(tier == LlmTier.PRO), locale="ru")
    if include:
        assert "транзит" in up.lower()
    else:
        assert "транзит" not in up.lower()


def test_max_tokens_for_tier():
    svc = LLMService()
    assert svc._max_tokens_for_tier(LlmTier.FREE) <= svc._max_tokens_for_tier(LlmTier.NATAL_FULL)
    assert svc._max_tokens_for_tier(LlmTier.NATAL_FULL) <= svc._max_tokens_for_tier(LlmTier.PRO)

"""
Фабрика клиентов для LLM-провайдеров.

Поддерживаемые провайдеры:
  - deepseek  — OpenAI-compatible API (api.deepseek.com)
  - grok      — OpenAI-compatible API (api.x.ai)
  - claude    — Anthropic SDK (api.anthropic.com)
"""
from __future__ import annotations

import enum

import httpx
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.core.config import settings


class LLMProvider(str, enum.Enum):
    DEEPSEEK = "deepseek"
    GROK = "grok"
    CLAUDE = "claude"


def _openai_timeout() -> httpx.Timeout:
    return httpx.Timeout(
        settings.LLM_HTTP_TIMEOUT_SECONDS,
        connect=min(30.0, float(settings.LLM_HTTP_TIMEOUT_SECONDS)),
    )


def create_client_for_provider(provider: LLMProvider) -> AsyncOpenAI | AsyncAnthropic:
    """Вернуть клиент для указанного провайдера."""
    if provider == LLMProvider.DEEPSEEK:
        return AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
            timeout=_openai_timeout(),
        )
    if provider == LLMProvider.GROK:
        return AsyncOpenAI(
            api_key=settings.GROK_API_KEY or "",
            base_url="https://api.x.ai/v1",
            timeout=_openai_timeout(),
        )
    if provider == LLMProvider.CLAUDE:
        return AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY or "",
            timeout=settings.LLM_HTTP_TIMEOUT_SECONDS,
        )
    raise ValueError(f"Unknown LLM provider: {provider}")


def model_for_provider(provider: LLMProvider) -> str:
    if provider == LLMProvider.DEEPSEEK:
        return settings.LLM_MODEL
    if provider == LLMProvider.GROK:
        return settings.GROK_MODEL
    if provider == LLMProvider.CLAUDE:
        return settings.CLAUDE_MODEL
    raise ValueError(f"Unknown LLM provider: {provider}")


def pricing_for_provider(provider: LLMProvider) -> dict[str, float]:
    """Вернуть тарифы провайдера (USD per 1M tokens)."""
    if provider == LLMProvider.DEEPSEEK:
        return {
            "input": settings.DEEPSEEK_INPUT_PRICE_PER_1M_USD,
            "output": settings.DEEPSEEK_OUTPUT_PRICE_PER_1M_USD,
            "cache_read": settings.DEEPSEEK_INPUT_PRICE_PER_1M_USD,
        }
    if provider == LLMProvider.GROK:
        return {
            "input": settings.GROK_INPUT_PRICE_PER_1M_USD,
            "output": settings.GROK_OUTPUT_PRICE_PER_1M_USD,
            "cache_read": settings.GROK_INPUT_PRICE_PER_1M_USD,
        }
    if provider == LLMProvider.CLAUDE:
        return {
            "input": settings.CLAUDE_INPUT_PRICE_PER_1M_USD,
            "output": settings.CLAUDE_OUTPUT_PRICE_PER_1M_USD,
            "cache_read": settings.CLAUDE_CACHE_READ_PRICE_PER_1M_USD,
        }
    raise ValueError(f"Unknown LLM provider: {provider}")

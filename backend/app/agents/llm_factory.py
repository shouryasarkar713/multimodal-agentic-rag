from __future__ import annotations

import os
import logging
from typing import Any

from langchain_openai import ChatOpenAI


def _build_chat_openai(
    *,
    model: str,
    api_key: str,
    base_url: str | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    timeout: float = 300.0,
    max_retries: int = 3,
    **extra: Any,
) -> ChatOpenAI:
    """Internal helper to build a ChatOpenAI instance with consistent defaults."""
    kwargs: dict[str, Any] = {
        "model": model,
        "openai_api_key": api_key,
        "temperature": temperature,
        "timeout": timeout,
        "max_retries": max_retries,
    }
    if base_url:
        kwargs["base_url"] = base_url
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    kwargs.update(extra)
    return ChatOpenAI(**kwargs)


def get_generation_llm() -> ChatOpenAI:
    """
    Factory for the *generation* LLM used by all agent nodes and eval metrics.

    Env vars (all optional — fall back to main settings):
        LLM_OPENAI_API_KEY   – API key for the generation model
        LLM_OPENAI_API_BASE  – Base URL (e.g. https://integrate.api.nvidia.com/v1)
        LLM_OPENAI_MODEL_NAME – Model name (e.g. nemotron-3-4b-instruct)
        LLM_TEMPERATURE       – Temperature (default 0.0)
        LLM_MAX_TOKENS        – Max tokens per request (optional)
    """
    # Lazy import settings to avoid circular deps
    from app.config import settings

    api_key = os.environ.get("LLM_OPENAI_API_KEY", settings.openai_api_key)
    base_url = os.environ.get("LLM_OPENAI_API_BASE", settings.openai_api_base)
    model_name = os.environ.get("LLM_OPENAI_MODEL_NAME", settings.openai_model_name)
    temperature = float(os.environ.get("LLM_TEMPERATURE", "0.0"))
    max_tokens_str = os.environ.get("LLM_MAX_TOKENS")
    max_tokens = int(max_tokens_str) if max_tokens_str else None

    # Helpful one-time log when override is active
    if (api_key != settings.openai_api_key
            or base_url != settings.openai_api_base
            or model_name != settings.openai_model_name):
        logging.info(
            "Generation LLM override active → model=%s, base=%s, key_set=%s",
            model_name, base_url, bool(api_key)
        )

    return _build_chat_openai(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_tool_llm() -> ChatOpenAI:
    """
    Factory for the tool-execution LLM (currently just re-uses generation LLM).
    Can be split later if tool calling requires different params.
    """
    return get_generation_llm()

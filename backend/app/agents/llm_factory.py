from __future__ import annotations

import os
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.runnables import Runnable


def _build_chat_openai(
    *,
    model: str,
    api_key: str,
    base_url: str | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    timeout: float = 45.0,
    max_retries: int = 2,
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


def get_generation_llm() -> Runnable:
    """
    Factory for the *generation* LLM used by all agent nodes and eval metrics.

    Env vars (all optional — fall back to main settings):
        LLM_OPENAI_API_KEY   – API key for the generation model
        LLM_OPENAI_API_BASE  – Base URL (e.g. https://integrate.api.nvidia.com/v1)
        LLM_OPENAI_MODEL_NAME – Model name (e.g. meta/llama-3.1-8b-instruct)
        LLM_TEMPERATURE       – Temperature (default 0.0)
        LLM_MAX_TOKENS        – Max tokens per request (optional)
    """
    # Lazy import settings to avoid circular deps
    from app.config import settings

    api_key = os.environ.get("LLM_OPENAI_API_KEY", settings.openai_api_key)
    base_url = os.environ.get("LLM_OPENAI_API_BASE", settings.openai_api_base)
    model_name = os.environ.get("LLM_OPENAI_MODEL_NAME", settings.openai_model_name)

    # Sanitize known unstable/EOL models on NVIDIA NIM
    if "mistral" in model_name.lower() or "llama-3.2-11b-vision" in model_name.lower():
        logging.info("Model '%s' is prone to connection resets on NVIDIA NIM. Using 'meta/llama-3.1-8b-instruct'.", model_name)
        model_name = "meta/llama-3.1-8b-instruct"

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

    primary_llm = _build_chat_openai(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=45.0,
        max_retries=2,
    )

    fallbacks: list[ChatOpenAI] = []

    # Fallback 1: If using NVIDIA NIM, meta/llama-3.1-8b-instruct if primary is different
    if "nvidia" in (base_url or "").lower() and model_name != "meta/llama-3.1-8b-instruct":
        fallbacks.append(
            _build_chat_openai(
                model="meta/llama-3.1-8b-instruct",
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=45.0,
                max_retries=2,
            )
        )

    # Fallback 2: Google Gemini (if configured in settings)
    gemini_key = settings.openai_api_key
    gemini_base = settings.openai_api_base
    if gemini_key and (gemini_key.startswith("AIzaSy") or "googleapis" in (gemini_base or "")):
        gemini_model = settings.openai_model_name if "gemini" in (settings.openai_model_name or "") else "gemini-1.5-flash"
        fallbacks.append(
            _build_chat_openai(
                model=gemini_model,
                api_key=gemini_key,
                base_url=gemini_base or "https://generativelanguage.googleapis.com/v1beta/openai/",
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=45.0,
                max_retries=2,
            )
        )

    if fallbacks:
        return primary_llm.with_fallbacks(fallbacks)
    return primary_llm


def get_tool_llm() -> Runnable:
    """
    Factory for the tool-execution LLM (currently just re-uses generation LLM).
    Can be split later if tool calling requires different params.
    """
    return get_generation_llm()

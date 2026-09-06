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
    timeout: float = 60.0,
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

    # Sanitize known EOL / deprecated models on NVIDIA NIM and Google
    is_nvidia = "nvidia" in (base_url or "").lower()
    if any(k in model_name.lower() for k in ["llama", "mistral", "minimax"]):
        if is_nvidia:
            logging.info("Model '%s' is EOL or deprecating on NVIDIA NIM. Mapping to active model 'google/gemma-4-31b-it'.", model_name)
            model_name = "google/gemma-4-31b-it"
        else:
            model_name = "gemini-3.6-flash"
    elif "gemini" in model_name.lower() and ("1.5" in model_name or "latest" in model_name or "2.5" in model_name):
        logging.info("Model '%s' is deprecated on Google API. Mapping to 'gemini-3.6-flash'.", model_name)
        model_name = "gemini-3.6-flash"

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
        timeout=60.0,
        max_retries=1,
    )

    fallbacks: list[ChatOpenAI] = []

    # If using NVIDIA NIM, build multi-model fallback chain among active models
    if is_nvidia:
        nvidia_models = [
            "google/gemma-4-31b-it",
            "poolside/laguna-xs-2.1",
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        ]
        for alt_model in nvidia_models:
            if alt_model != model_name:
                fallbacks.append(
                    _build_chat_openai(
                        model=alt_model,
                        api_key=api_key,
                        base_url=base_url,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=60.0,
                        max_retries=1,
                    )
                )

    # Fallback 2: Google Gemini 3.6 Flash (if configured in settings)
    gemini_key = settings.openai_api_key
    gemini_base = settings.openai_api_base or "https://generativelanguage.googleapis.com/v1beta/openai/"
    if gemini_key and (gemini_key.startswith("AIzaSy") or "googleapis" in (gemini_base or "")):
        fallbacks.append(
            _build_chat_openai(
                model="gemini-3.6-flash",
                api_key=gemini_key,
                base_url=gemini_base,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=60.0,
                max_retries=1,
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

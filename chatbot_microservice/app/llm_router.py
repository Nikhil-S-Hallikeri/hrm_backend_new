from __future__ import annotations

import logging
import time
from collections.abc import Iterable

from openai import APIError, APITimeoutError, OpenAI, RateLimitError

from app.config import get_settings

logger = logging.getLogger(__name__)

# Errors worth retrying across providers (transient infra failures)
RETRYABLE_ERRORS = (RateLimitError, APITimeoutError)

# Errors that are our fault or the model's — don't retry, fail fast
FATAL_ERRORS = (ValueError, KeyError, RuntimeError)

# Per-provider timeouts in seconds
PROVIDER_TIMEOUTS: dict[str, int] = {
    "groq": 6,
    "openrouter": 20,
    "openai": 15,
}

# How long to wait after a RateLimitError before moving to next provider
RATE_LIMIT_BACKOFF = 0.5  # seconds


def _client(api_key: str, base_url: str | None = None, timeout: int = 10) -> OpenAI:
    if not api_key:
        raise RuntimeError("Provider is not configured — API key is missing")
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
    return OpenAI(api_key=api_key, timeout=timeout)


def _chat(
    client: OpenAI,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError(f"Model {model!r} returned an empty response")
    return content.strip()


def _openrouter_models(settings) -> list[str]:
    return settings.openrouter_models or [settings.openrouter_model]


def _provider_sequence(provider_order: Iterable[str] | None, settings) -> list[str]:
    if provider_order:
        return [p.strip().lower() for p in provider_order if p.strip()]
    if settings.ai_provider == "openrouter":
        return ["openrouter"]
    if settings.ai_provider == "openai":
        return ["openai"]
    if settings.ai_provider == "groq":
        return ["groq"]
    return ["groq", "openrouter", "openai"]


def generate_llm_response(
    messages: list[dict[str, str]],
    temperature: float = 0.25,
    max_tokens: int = 180,
    provider_order: Iterable[str] | None = None,
    lead_status: str = "Cold",  # noqa: ARG001
    ai_config: Any = None,
) -> str:
    """
    Try configured LLM provider in order, prioritizing user-defined tenant AIConfig settings if available.

    Returns the model's response string.
    Raises RuntimeError if all providers fail.
    """
    settings = get_settings()
    errors: list[str] = []

    # Check if custom AIConfig specifies provider and API key
    if ai_config:
        custom_provider = getattr(ai_config, 'llm_provider', None) or (ai_config.get('llm_provider') if isinstance(ai_config, dict) else None)
        custom_model = getattr(ai_config, 'model_name', None) or (ai_config.get('model_name') if isinstance(ai_config, dict) else None)
        custom_key = getattr(ai_config, 'api_key', None) or (ai_config.get('api_key') if isinstance(ai_config, dict) else None)

        if custom_provider and custom_key:
            custom_provider = custom_provider.strip().lower()
            timeout = PROVIDER_TIMEOUTS.get(custom_provider, 15)
            try:
                if custom_provider == "gemini":
                    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
                    model = custom_model or "gemini-2.5-flash"
                elif custom_provider == "groq":
                    base_url = "https://api.groq.com/openai/v1"
                    model = custom_model or "llama-3.3-70b-versatile"
                elif custom_provider == "openrouter":
                    base_url = "https://openrouter.ai/api/v1"
                    model = custom_model or "openrouter/free"
                else:
                    base_url = None
                    model = custom_model or "gpt-4o-mini"

                return _chat(
                    _client(custom_key, base_url, timeout),
                    model,
                    messages,
                    temperature,
                    max_tokens,
                )
            except Exception as exc:
                msg = f"Custom tenant provider {custom_provider!r} error ({type(exc).__name__}): {exc}"
                logger.warning(msg)
                errors.append(msg)

    # Fallback sequence to environment settings
    sequence = _provider_sequence(provider_order, settings)
    for provider in sequence:
        timeout = PROVIDER_TIMEOUTS.get(provider, 10)

        if provider == "gemini":
            gemini_key = os.getenv("GEMINI_API_KEY", "")
            if not gemini_key:
                continue
            try:
                return _chat(
                    _client(gemini_key, "https://generativelanguage.googleapis.com/v1beta/openai/", timeout),
                    os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                    messages,
                    temperature,
                    max_tokens,
                )
            except Exception as exc:
                msg = f"Gemini error ({type(exc).__name__}): {exc}"
                logger.warning(msg)
                errors.append(msg)

        elif provider == "groq":
            if not settings.groq_api_key:
                continue
            try:
                return _chat(
                    _client(settings.groq_api_key, "https://api.groq.com/openai/v1", timeout),
                    settings.groq_model,
                    messages,
                    temperature,
                    max_tokens,
                )
            except RateLimitError as exc:
                msg = f"Groq rate-limited: {exc}"
                logger.warning(msg)
                errors.append(msg)
                time.sleep(RATE_LIMIT_BACKOFF)
            except RETRYABLE_ERRORS as exc:
                msg = f"Groq transient error ({type(exc).__name__}): {exc}"
                logger.warning(msg)
                errors.append(msg)
            except FATAL_ERRORS as exc:
                msg = f"Groq fatal error ({type(exc).__name__}): {exc}"
                logger.error(msg)
                errors.append(msg)
                break

        elif provider == "openrouter":
            if not settings.openrouter_api_key:
                continue
            for model in _openrouter_models(settings):
                try:
                    return _chat(
                        _client(settings.openrouter_api_key, "https://openrouter.ai/api/v1", timeout),
                        model,
                        messages,
                        temperature,
                        max_tokens,
                    )
                except RateLimitError as exc:
                    msg = f"OpenRouter model {model!r} rate-limited: {exc}"
                    logger.warning(msg)
                    errors.append(msg)
                    time.sleep(RATE_LIMIT_BACKOFF)
                except RETRYABLE_ERRORS as exc:
                    msg = f"OpenRouter model {model!r} transient error: {exc}"
                    logger.warning(msg)
                    errors.append(msg)
                except FATAL_ERRORS as exc:
                    msg = f"OpenRouter model {model!r} fatal error: {exc}"
                    logger.error(msg)
                    errors.append(msg)
                    break

        elif provider == "openai":
            if not settings.openai_api_key:
                continue
            try:
                return _chat(
                    _client(settings.openai_api_key, timeout=timeout),
                    settings.openai_model,
                    messages,
                    temperature,
                    max_tokens,
                )
            except RateLimitError as exc:
                msg = f"OpenAI rate-limited: {exc}"
                logger.warning(msg)
                errors.append(msg)
                time.sleep(RATE_LIMIT_BACKOFF)
            except RETRYABLE_ERRORS as exc:
                msg = f"OpenAI transient error ({type(exc).__name__}): {exc}"
                logger.warning(msg)
                errors.append(msg)
            except FATAL_ERRORS as exc:
                msg = f"OpenAI fatal error ({type(exc).__name__}): {exc}"
                logger.error(msg)
                errors.append(msg)
                break

    error_summary = "\n".join(errors)
    logger.error("All LLM providers failed:\n%s", error_summary)
    raise RuntimeError(f"All LLM providers failed:\n{error_summary}")
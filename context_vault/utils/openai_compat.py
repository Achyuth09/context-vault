"""OpenAI SDK client pointed at OpenRouter (Qwen, etc.)."""

from __future__ import annotations

import time
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError

from context_vault import config
from context_vault.utils.logging import get_logger

log = get_logger("context_vault.openai_compat")


class OpenAICompatError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _extra_body() -> dict[str, Any] | None:
    """Build OpenRouter extra_body (provider pin + reasoning) from config."""
    body: dict[str, Any] = {}
    if config.OPENROUTER_PROVIDER_ONLY:
        providers = [p.strip() for p in config.OPENROUTER_PROVIDER_ONLY.split(",") if p.strip()]
        if providers:
            body["provider"] = {
                "only": providers,
                "allow_fallbacks": config.OPENROUTER_ALLOW_FALLBACKS,
            }
    if config.OPENROUTER_REASONING:
        body["reasoning"] = {"enabled": True}
    return body or None


def get_openrouter_client(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout: float = 90.0,
) -> OpenAI:
    api_key = api_key if api_key is not None else config.OPENROUTER_API_KEY
    base_url = (base_url or config.OPENROUTER_BASE_URL).rstrip("/")
    if not api_key:
        raise OpenAICompatError(
            "OPENROUTER_API_KEY missing. Set it in .env (see .env.example)."
        )
    return OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
        default_headers={
            "HTTP-Referer": config.OPENROUTER_SITE_URL,
            "X-Title": config.OPENROUTER_APP_NAME,
        },
    )


def chat_completion(
    *,
    messages: list[dict[str, Any]],
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.1,
    timeout: float = 90.0,
) -> str:
    """
    chat.completions.create via OpenAI SDK → OpenRouter.
    Retries rate limits / transient errors using config backoff knobs.
    """
    model = model or config.OPENROUTER_MODEL
    client = get_openrouter_client(api_key=api_key, base_url=base_url, timeout=timeout)
    extra = _extra_body()
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if extra:
        kwargs["extra_body"] = extra

    last_err: Exception | None = None
    for attempt in range(1, config.MAX_API_RETRIES + 1):
        try:
            response = client.chat.completions.create(**kwargs)
            choices = response.choices or []
            if not choices:
                raise OpenAICompatError("OpenRouter returned no choices")
            content = choices[0].message.content or ""
            text = str(content).strip()
            if not text:
                raise OpenAICompatError("OpenRouter returned empty content")
            return text

        except RateLimitError as e:
            last_err = e
            if attempt == config.MAX_API_RETRIES:
                raise OpenAICompatError("OpenRouter rate limit (429)", status_code=429) from e
            delay = config.API_BASE_DELAY * (2 ** (attempt - 1))
            log.warning(
                "[429] openrouter attempt %s/%s — wait %ss...",
                attempt,
                config.MAX_API_RETRIES,
                delay,
            )
            time.sleep(delay)

        except APIStatusError as e:
            last_err = e
            code = getattr(e, "status_code", None)
            if code in (400, 401, 403):
                raise OpenAICompatError(
                    f"OpenRouter auth/config error ({code}): {e}",
                    status_code=code,
                ) from e
            if code in (500, 502, 503, 504) and attempt < config.MAX_API_RETRIES:
                delay = config.API_BASE_DELAY * (2 ** (attempt - 1))
                log.warning(
                    "[%s] openrouter attempt %s/%s — wait %ss...",
                    code,
                    attempt,
                    config.MAX_API_RETRIES,
                    delay,
                )
                time.sleep(delay)
                continue
            raise OpenAICompatError(f"OpenRouter HTTP {code}: {e}", status_code=code) from e

        except (APIConnectionError, APITimeoutError, ConnectionError, TimeoutError) as e:
            last_err = e
            if attempt == config.MAX_API_RETRIES:
                raise OpenAICompatError(f"Network error talking to OpenRouter: {e}") from e
            delay = config.API_BASE_DELAY * (2 ** (attempt - 1))
            log.warning(
                "[network] openrouter attempt %s/%s — wait %ss...",
                attempt,
                config.MAX_API_RETRIES,
                delay,
            )
            time.sleep(delay)

    raise OpenAICompatError(f"Unreachable: {last_err}")

"""Retry helpers for Gemini / HTTP-ish client errors."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from google.genai import errors

from context_vault import config
from context_vault.utils.logging import get_logger

T = TypeVar("T")
log = get_logger("context_vault.retry")


def with_backoff(fn: Callable[[], T], *, label: str = "api") -> T:
    """
    Run fn(); retry on 429 / 5xx / network with exponential backoff.
    Uses config.MAX_API_RETRIES and config.API_BASE_DELAY.
    """
    for attempt in range(1, config.MAX_API_RETRIES + 1):
        try:
            return fn()
        except errors.ClientError as e:
            if e.code == 429:
                if attempt == config.MAX_API_RETRIES:
                    raise RuntimeError(
                        "Rate limit (429) too many times. Wait and retry."
                    ) from e
                delay = config.API_BASE_DELAY * (2 ** (attempt - 1))
                log.warning(
                    "[429 rate limit] %s attempt %s/%s — wait %ss...",
                    label,
                    attempt,
                    config.MAX_API_RETRIES,
                    delay,
                )
                time.sleep(delay)
            elif e.code in (400, 401, 403):
                raise RuntimeError(
                    f"Config/auth error ({e.code}): check API key and model name."
                ) from e
            else:
                raise
        except errors.ServerError as e:
            if attempt == config.MAX_API_RETRIES:
                raise RuntimeError("Gemini server error — try again later.") from e
            delay = config.API_BASE_DELAY * (2 ** (attempt - 1))
            log.warning(
                "[server %s] %s attempt %s/%s — wait %ss...",
                e.code,
                label,
                attempt,
                config.MAX_API_RETRIES,
                delay,
            )
            time.sleep(delay)
        except (ConnectionError, TimeoutError) as e:
            if attempt == config.MAX_API_RETRIES:
                raise RuntimeError("Network error talking to Gemini.") from e
            delay = config.API_BASE_DELAY * (2 ** (attempt - 1))
            log.warning(
                "[network] %s attempt %s/%s — wait %ss...",
                label,
                attempt,
                config.MAX_API_RETRIES,
                delay,
            )
            time.sleep(delay)

    raise RuntimeError("Unreachable")

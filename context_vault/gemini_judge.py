"""Compat shim — prefer strategies.conflict.gemini / get_conflict_judge."""

from __future__ import annotations

from typing import Any

from context_vault.strategies.conflict.factory import get_conflict_judge
from context_vault.strategies.conflict.gemini import (
    JUDGE_PROMPT,
    GeminiConflictJudge,
    parse_judge_json,
)
from context_vault.utils.retry import with_backoff

# Old name used in tests
_parse_judge_json = parse_judge_json


def generate_with_retry(prompt: str, *, model: str | None = None) -> str:
    """Backward-compatible wrapper around retry util + Gemini client."""
    from google import genai
    from google.genai import types

    from context_vault import config

    if not config.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY missing. Copy .env.example → .env and set your key."
        )
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    use_model = model or config.GEMINI_MODEL

    def _call() -> str:
        response = client.models.generate_content(
            model=use_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            ),
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned empty text")
        return text

    return with_backoff(_call, label="gemini")


def do_they_contradict(fact_a: str, fact_b: str) -> dict[str, Any]:
    """Ask the configured conflict judge (default: gemini)."""
    return get_conflict_judge().judge(fact_a, fact_b)


__all__ = [
    "JUDGE_PROMPT",
    "GeminiConflictJudge",
    "do_they_contradict",
    "generate_with_retry",
    "parse_judge_json",
    "_parse_judge_json",
]

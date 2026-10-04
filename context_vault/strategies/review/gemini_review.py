"""Gemini PR review judge (optional)."""

from __future__ import annotations

from typing import Any

from google import genai
from google.genai import types

from context_vault import config
from context_vault.strategies.review._common import (
    REVIEW_SYSTEM,
    build_user_prompt,
    parse_findings_json,
)
from context_vault.utils.retry import with_backoff


class GeminiReviewJudge:
    name = "gemini"

    def review(
        self,
        *,
        diff: str,
        policies: list[dict[str, Any]],
        title: str = "",
        body: str = "",
    ) -> list[dict[str, Any]]:
        if not config.GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY missing. Copy .env.example → .env and set your key."
            )
        prompt = build_user_prompt(diff=diff, policies=policies, title=title, body=body)
        full = f"{REVIEW_SYSTEM}\n\n{prompt}"
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        model = config.GEMINI_MODEL

        def _call() -> str:
            response = client.models.generate_content(
                model=model,
                contents=full,
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

        raw = with_backoff(_call, label="gemini-review")
        return parse_findings_json(raw)

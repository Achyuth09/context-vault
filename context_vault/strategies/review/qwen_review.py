"""Qwen / OpenRouter PR review judge."""

from __future__ import annotations

from typing import Any

from context_vault import config
from context_vault.strategies.review._common import (
    REVIEW_SYSTEM,
    build_user_prompt,
    parse_findings_json,
)
from context_vault.utils.openai_compat import chat_completion


class QwenReviewJudge:
    name = "qwen"

    def review(
        self,
        *,
        diff: str,
        policies: list[dict[str, Any]],
        title: str = "",
        body: str = "",
    ) -> list[dict[str, Any]]:
        prompt = build_user_prompt(diff=diff, policies=policies, title=title, body=body)
        raw = chat_completion(
            messages=[
                {"role": "system", "content": REVIEW_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            model=config.OPENROUTER_MODEL,
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL,
        )
        return parse_findings_json(raw)

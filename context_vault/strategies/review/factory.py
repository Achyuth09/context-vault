"""Build ReviewJudgeStrategy from config."""

from __future__ import annotations

from context_vault import config
from context_vault.strategies.base import ReviewJudgeStrategy
from context_vault.strategies.review.gemini_review import GeminiReviewJudge
from context_vault.strategies.review.heuristic_review import HeuristicReviewJudge
from context_vault.strategies.review.qwen_review import QwenReviewJudge

_REGISTRY: dict[str, type] = {
    "qwen": QwenReviewJudge,
    "gemini": GeminiReviewJudge,
    "heuristic": HeuristicReviewJudge,
}


def get_review_judge(name: str | None = None) -> ReviewJudgeStrategy:
    key = (name or config.REVIEW_LLM).strip().lower()
    # aliases
    if key in ("openrouter", "qwen3", "qwen3.8"):
        key = "qwen"
    cls = _REGISTRY.get(key)
    if cls is None:
        known = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown REVIEW_LLM={key!r}. Choose: {known}")
    return cls()

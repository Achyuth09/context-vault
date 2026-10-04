"""Build ConflictJudgeStrategy from config."""

from __future__ import annotations

from context_vault import config
from context_vault.strategies.base import ConflictJudgeStrategy
from context_vault.strategies.conflict.gemini import GeminiConflictJudge
from context_vault.strategies.conflict.heuristic import HeuristicConflictJudge

_REGISTRY: dict[str, type] = {
    "gemini": GeminiConflictJudge,
    "heuristic": HeuristicConflictJudge,
}


def get_conflict_judge(name: str | None = None) -> ConflictJudgeStrategy:
    key = (name or config.CONFLICT_JUDGE).strip().lower()
    cls = _REGISTRY.get(key)
    if cls is None:
        known = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown CONFLICT_JUDGE={key!r}. Choose: {known}")
    return cls()

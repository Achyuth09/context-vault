"""Build RetrievalStrategy from config."""

from __future__ import annotations

from context_vault import config
from context_vault.strategies.base import RetrievalStrategy
from context_vault.strategies.retrieval.filter_stale import FilterStaleRetrieval
from context_vault.strategies.retrieval.recency_boosted import RecencyBoostedRetrieval
from context_vault.strategies.retrieval.similarity import SimilarityRetrieval

_REGISTRY: dict[str, type] = {
    "similarity": SimilarityRetrieval,
    "recency_boosted": RecencyBoostedRetrieval,
    "filter_stale": FilterStaleRetrieval,
}


def get_retrieval_strategy(name: str | None = None) -> RetrievalStrategy:
    key = (name or config.RETRIEVAL_STRATEGY).strip().lower()
    cls = _REGISTRY.get(key)
    if cls is None:
        known = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown RETRIEVAL_STRATEGY={key!r}. Choose: {known}")
    return cls()

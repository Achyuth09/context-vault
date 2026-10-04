"""get_context — retrieve via configured RetrievalStrategy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from context_vault import config
from context_vault.models import ContextHit, hits_as_dicts
from context_vault.store import get_collection
from context_vault.strategies.retrieval.factory import get_retrieval_strategy
from context_vault.utils.age import age_bucket

# Re-exports for existing imports / tests
__all__ = [
    "ContextHit",
    "age_bucket",
    "get_context",
    "hits_as_dicts",
]


def get_context(
    query: str,
    *,
    top_k: int | None = None,
    chroma_dir: Path | str | None = None,
    collection_name: str | None = None,
    strategy: str | None = None,
) -> list[ContextHit]:
    """
    Semantic search with provenance + recency.

    Retrieval algorithm comes from config.RETRIEVAL_STRATEGY
    (or the strategy= override).
    """
    top_k = top_k if top_k is not None else config.DEFAULT_TOP_K
    collection = get_collection(chroma_dir, collection_name)
    retriever = get_retrieval_strategy(strategy)
    return retriever.retrieve(collection, query, top_k=top_k)

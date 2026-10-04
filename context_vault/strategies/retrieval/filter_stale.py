"""Drop age-stale hits unless explicitly contested (keep contested visible)."""

from __future__ import annotations

from chromadb.api.models.Collection import Collection

from context_vault.models import ContextHit
from context_vault.strategies.retrieval.similarity import SimilarityRetrieval


class FilterStaleRetrieval:
    name = "filter_stale"

    def __init__(self) -> None:
        self._base = SimilarityRetrieval()

    def retrieve(
        self,
        collection: Collection,
        query: str,
        *,
        top_k: int,
    ) -> list[ContextHit]:
        pool = min(max(top_k * 4, top_k), collection.count() or top_k)
        hits = self._base.retrieve(collection, query, top_k=pool)
        kept = [
            h
            for h in hits
            if h.age_bucket != "stale" or h.status == "contested"
        ]
        # If everything filtered out, fall back to unfiltered top_k
        if not kept:
            return hits[:top_k]
        return kept[:top_k]

"""Re-rank similarity hits with an age penalty (prefer fresher)."""

from __future__ import annotations

from chromadb.api.models.Collection import Collection

from context_vault import config
from context_vault.models import ContextHit
from context_vault.strategies.retrieval.similarity import SimilarityRetrieval


class RecencyBoostedRetrieval:
    name = "recency_boosted"

    def __init__(self, weight: float | None = None) -> None:
        self.weight = config.RECENCY_WEIGHT if weight is None else weight
        self._base = SimilarityRetrieval()

    def retrieve(
        self,
        collection: Collection,
        query: str,
        *,
        top_k: int,
    ) -> list[ContextHit]:
        # Fetch a wider pool then re-rank
        pool = min(max(top_k * 3, top_k), collection.count() or top_k)
        hits = self._base.retrieve(collection, query, top_k=pool)

        def score(h: ContextHit) -> float:
            dist = h.distance if h.distance is not None else 1.0
            age = h.age_days if h.age_days is not None else 365.0
            # lower is better (like distance)
            return dist + self.weight * age

        hits.sort(key=score)
        return hits[:top_k]

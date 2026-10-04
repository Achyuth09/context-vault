"""Plain cosine similarity top-k (current default behavior)."""

from __future__ import annotations

from chromadb.api.models.Collection import Collection

from context_vault.models import ContextHit
from context_vault.strategies.retrieval._common import hits_from_query_result


class SimilarityRetrieval:
    name = "similarity"

    def retrieve(
        self,
        collection: Collection,
        query: str,
        *,
        top_k: int,
    ) -> list[ContextHit]:
        count = collection.count()
        if count == 0:
            return []
        result = collection.query(
            query_texts=[query],
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"],
        )
        return hits_from_query_result(result)

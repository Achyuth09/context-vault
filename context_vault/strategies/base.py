"""Strategy interfaces (Protocols) for swappable behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from chromadb.api.models.Collection import Collection
    from context_vault.models import ContextHit


@runtime_checkable
class ChunkingStrategy(Protocol):
    name: str

    def chunk(self, text: str) -> list[str]:
        """Split document text into chunks."""
        ...


@runtime_checkable
class RetrievalStrategy(Protocol):
    name: str

    def retrieve(
        self,
        collection: Collection,
        query: str,
        *,
        top_k: int,
    ) -> list[ContextHit]:
        """Return ranked ContextHit list for a query."""
        ...


@runtime_checkable
class ConflictJudgeStrategy(Protocol):
    name: str

    def judge(self, fact_a: str, fact_b: str) -> dict[str, Any]:
        """
        Decide if two facts contradict.

        Returns at least: {"contradict": bool, "reason": str}
        May include "raw" for LLM judges.
        """
        ...


@runtime_checkable
class ReviewJudgeStrategy(Protocol):
    name: str

    def review(
        self,
        *,
        diff: str,
        policies: list[dict[str, Any]],
        title: str = "",
        body: str = "",
    ) -> list[dict[str, Any]]:
        """
        Return findings: each with severity, rule, evidence, suggestion.
        Optional keys: policy_doc_id, line_hint.
        """
        ...

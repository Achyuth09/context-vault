"""Shared domain models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ContextHit:
    """One retrieved chunk plus provenance and health."""

    text: str
    doc_id: str
    source_path: str
    chunk_index: int
    updated_at: str
    ingested_at: str
    status: str
    age_days: float | None
    age_bucket: str  # fresh | aging | stale | unknown
    distance: float | None  # lower = closer (cosine distance from Chroma)


def hits_as_dicts(hits: list[ContextHit]) -> list[dict[str, Any]]:
    return [asdict(h) for h in hits]

"""Shared hit-building for retrieval strategies."""

from __future__ import annotations

from typing import Any

from context_vault.models import ContextHit
from context_vault.utils.age import age_bucket


def resolve_status(stored: str, bucket: str) -> str:
    if stored in ("contested", "stale"):
        return stored
    return bucket


def hit_from_meta(
    text: str,
    meta: dict[str, Any] | None,
    distance: float | None,
) -> ContextHit:
    meta = meta or {}
    updated_at = str(meta.get("updated_at") or "")
    days, bucket = age_bucket(updated_at)
    stored = str(meta.get("status") or "fresh")
    return ContextHit(
        text=text or "",
        doc_id=str(meta.get("doc_id") or ""),
        source_path=str(meta.get("source_path") or ""),
        chunk_index=int(meta.get("chunk_index") or 0),
        updated_at=updated_at,
        ingested_at=str(meta.get("ingested_at") or ""),
        status=resolve_status(stored, bucket),
        age_days=round(days, 2) if days is not None else None,
        age_bucket=bucket,
        distance=float(distance) if distance is not None else None,
    )


def hits_from_query_result(result: dict[str, Any]) -> list[ContextHit]:
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    return [
        hit_from_meta(text or "", meta, dist)
        for text, meta, dist in zip(docs, metas, distances)
    ]

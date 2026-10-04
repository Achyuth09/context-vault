"""Chroma persistence + provenance-aware metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions

from context_vault import config
from context_vault.utils.timeutil import file_mtime_iso, utc_now_iso

# Re-export for existing imports
__all__ = [
    "utc_now_iso",
    "file_mtime_iso",
    "get_embed_fn",
    "get_collection",
    "clear_collection",
    "delete_by_doc_id",
    "build_chunk_metadata",
    "set_status_for_doc",
    "set_status_for_ids",
]


def get_embed_fn():
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=config.EMBEDDING_MODEL
    )


def get_collection(
    chroma_dir: Path | str | None = None,
    collection_name: str | None = None,
) -> Collection:
    chroma_dir = Path(chroma_dir or config.DEFAULT_CHROMA_DIR)
    collection_name = collection_name or config.DEFAULT_COLLECTION
    chroma_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(chroma_dir))
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=get_embed_fn(),
        metadata={"hnsw:space": "cosine"},
    )


def clear_collection(collection: Collection) -> int:
    count = collection.count()
    if count > 0:
        collection.delete(ids=collection.get()["ids"])
    return count


def delete_by_doc_id(collection: Collection, doc_id: str) -> int:
    """Remove all chunks for one document (re-ingest friendly)."""
    existing = collection.get(where={"doc_id": doc_id})
    ids = existing.get("ids") or []
    if ids:
        collection.delete(ids=ids)
    return len(ids)


def build_chunk_metadata(
    *,
    doc_id: str,
    source_path: Path,
    chunk_index: int,
    updated_at: str,
    ingested_at: str | None = None,
    status: str = "fresh",
) -> dict[str, Any]:
    """
    Provenance fields stored per chunk.

    doc_id       — stable id (usually filename stem)
    source_path  — where the text came from
    updated_at   — when the *source* was last modified (or marked)
    ingested_at  — when we indexed this chunk
    status       — fresh | aging | stale | contested (Phase 2+ uses contested)
    chunk_index  — order within the document
    """
    return {
        "doc_id": doc_id,
        "source_path": str(source_path.resolve()),
        "filename": source_path.name,
        "chunk_index": chunk_index,
        "updated_at": updated_at,
        "ingested_at": ingested_at or utc_now_iso(),
        "status": status,
    }


def set_status_for_doc(
    collection: Collection,
    doc_id: str,
    status: str,
    *,
    extra: dict[str, Any] | None = None,
) -> int:
    """Update status (and optional extra fields) on every chunk of doc_id."""
    existing = collection.get(where={"doc_id": doc_id}, include=["metadatas"])
    ids = existing.get("ids") or []
    metas = existing.get("metadatas") or []
    if not ids:
        return 0

    updated: list[dict[str, Any]] = []
    for meta in metas:
        new_meta = dict(meta or {})
        new_meta["status"] = status
        if extra:
            new_meta.update(extra)
        updated.append(new_meta)

    collection.update(ids=ids, metadatas=updated)
    return len(ids)


def set_status_for_ids(
    collection: Collection,
    ids: list[str],
    status: str,
    *,
    extra: dict[str, Any] | None = None,
) -> int:
    """Update status on specific chunk ids."""
    if not ids:
        return 0
    existing = collection.get(ids=ids, include=["metadatas"])
    got_ids = existing.get("ids") or []
    metas = existing.get("metadatas") or []
    if not got_ids:
        return 0

    updated: list[dict[str, Any]] = []
    for meta in metas:
        new_meta = dict(meta or {})
        new_meta["status"] = status
        if extra:
            new_meta.update(extra)
        updated.append(new_meta)

    collection.update(ids=got_ids, metadatas=updated)
    return len(got_ids)

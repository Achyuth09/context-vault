"""Ingest markdown/text docs into Chroma with provenance metadata."""

from __future__ import annotations

from pathlib import Path

from context_vault import config
from context_vault.strategies.chunking.factory import get_chunking_strategy
from context_vault.store import (
    build_chunk_metadata,
    clear_collection,
    delete_by_doc_id,
    get_collection,
)
from context_vault.utils.logging import get_logger
from context_vault.utils.paths import discover_docs, doc_id_for
from context_vault.utils.timeutil import file_mtime_iso, utc_now_iso

log = get_logger("context_vault.ingest")

# Re-export for callers / tests
__all__ = ["discover_docs", "doc_id_for", "ingest_docs"]


def ingest_docs(
    docs_dir: Path | str | None = None,
    *,
    chroma_dir: Path | str | None = None,
    collection_name: str | None = None,
    chunk_size: int | None = None,
    overlap: int | None = None,
    chunk_strategy: str | None = None,
    reset: bool = True,
) -> dict:
    """
    Load all markdown/txt under docs_dir → chunk → embed → store.

    Chunking comes from config.CHUNK_STRATEGY (override with chunk_strategy=).
    """
    docs_dir = Path(docs_dir or config.DEFAULT_DOCS_DIR)
    chunker = get_chunking_strategy(
        chunk_strategy,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    files = discover_docs(docs_dir)
    collection = get_collection(chroma_dir, collection_name)

    if reset:
        cleared = clear_collection(collection)
        if cleared:
            log.info("Cleared %s old chunks", cleared)
            print(f"Cleared {cleared} old chunks")

    ingested_at = utc_now_iso()
    all_ids: list[str] = []
    all_docs: list[str] = []
    all_meta: list[dict] = []
    per_file: list[dict] = []

    log.info("Chunking with strategy=%s", chunker.name)

    for path in files:
        text = path.read_text(encoding="utf-8")
        pieces = chunker.chunk(text)
        doc_id = doc_id_for(path, docs_dir)
        updated_at = file_mtime_iso(path)

        if not reset:
            delete_by_doc_id(collection, doc_id)

        for i, piece in enumerate(pieces):
            all_ids.append(f"{doc_id}__{i}")
            all_docs.append(piece)
            all_meta.append(
                build_chunk_metadata(
                    doc_id=doc_id,
                    source_path=path,
                    chunk_index=i,
                    updated_at=updated_at,
                    ingested_at=ingested_at,
                    status="fresh",
                )
            )

        per_file.append(
            {
                "doc_id": doc_id,
                "path": str(path),
                "chunks": len(pieces),
                "updated_at": updated_at,
                "chunk_strategy": chunker.name,
            }
        )
        print(f"  {doc_id}: {len(pieces)} chunks (updated_at={updated_at})")

    if not all_docs:
        print("Nothing to index.")
        return {"files": 0, "chunks": 0, "details": [], "chunk_strategy": chunker.name}

    collection.add(ids=all_ids, documents=all_docs, metadatas=all_meta)
    total = collection.count()
    print(f"Indexed {len(all_docs)} chunks from {len(files)} files (collection: {total})")
    return {
        "files": len(files),
        "chunks": len(all_docs),
        "details": per_file,
        "chunk_strategy": chunker.name,
    }

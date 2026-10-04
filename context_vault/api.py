"""
Phase 4 — tiny HTTP bridge for the context-health dashboard.

  uvicorn context_vault.api:app --reload --port 8000

Same data as CLI/MCP; JSON for the Next.js UI.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from context_vault.conflicts import load_conflicts, mark_stale
from context_vault.get_context import get_context, hits_as_dicts
from context_vault.store import get_collection

_DOC_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")

app = FastAPI(
    title="Context Vault API",
    description="Health + provenance for the dashboard (Phase 4).",
    version="0.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "context-vault"}


@app.get("/api/stats")
def stats() -> dict[str, Any]:
    collection = get_collection()
    count = collection.count()
    by_doc: dict[str, int] = {}
    by_status: dict[str, int] = {}

    if count:
        data = collection.get(include=["metadatas"])
        for meta in data.get("metadatas") or []:
            meta = meta or {}
            doc_id = str(meta.get("doc_id") or "?")
            by_doc[doc_id] = by_doc.get(doc_id, 0) + 1
            st = str(meta.get("status") or "?")
            by_status[st] = by_status.get(st, 0) + 1

    conflicts = load_conflicts()
    real = [c for c in conflicts if c.get("contradict")]
    return {
        "chunks": count,
        "by_doc": by_doc,
        "by_status": by_status,
        "conflicts_total": len(conflicts),
        "conflicts_real": len(real),
    }


@app.get("/api/chunks")
def chunks() -> dict[str, Any]:
    """All indexed chunks with provenance (dashboard table)."""
    collection = get_collection()
    if collection.count() == 0:
        return {"chunks": []}

    data = collection.get(include=["documents", "metadatas"])
    rows: list[dict[str, Any]] = []
    ids = data.get("ids") or []
    docs = data.get("documents") or []
    metas = data.get("metadatas") or []

    for chunk_id, text, meta in zip(ids, docs, metas):
        meta = meta or {}
        rows.append(
            {
                "id": chunk_id,
                "text": text or "",
                "doc_id": str(meta.get("doc_id") or ""),
                "status": str(meta.get("status") or "fresh"),
                "updated_at": str(meta.get("updated_at") or ""),
                "ingested_at": str(meta.get("ingested_at") or ""),
                "chunk_index": int(meta.get("chunk_index") or 0),
                "source_path": str(meta.get("source_path") or ""),
            }
        )

    rows.sort(key=lambda r: (r["doc_id"], r["chunk_index"]))
    return {"chunks": rows}


@app.get("/api/conflicts")
def conflicts(only_real: bool = Query(False, description="Only contradict=true")) -> dict[str, Any]:
    records = load_conflicts()
    if only_real:
        records = [c for c in records if c.get("contradict")]
    return {"conflicts": records, "count": len(records)}


@app.post("/api/docs/{doc_id}/stale")
def mark_doc_stale(doc_id: str) -> dict[str, Any]:
    """Explicit stale stamp for every chunk of one doc. Same as CLI mark-stale."""
    if not _DOC_ID.fullmatch(doc_id):
        raise HTTPException(status_code=400, detail="invalid doc_id")
    result = mark_stale(doc_id)
    if result["chunks_updated"] == 0:
        raise HTTPException(status_code=404, detail=f"No chunks for doc_id={doc_id}")
    return result


@app.get("/api/query")
def query(q: str = Query(..., min_length=1), top_k: int = Query(5, ge=1, le=20)) -> dict[str, Any]:
    hits = get_context(q, top_k=top_k)
    return {"query": q, "count": len(hits), "hits": hits_as_dicts(hits)}

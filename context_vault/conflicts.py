"""Phase 2: mark_stale, flag_conflict, detect_conflicts."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from context_vault import config
from context_vault.get_context import get_context
from context_vault.models import ContextHit
from context_vault.store import get_collection, set_status_for_doc, set_status_for_ids
from context_vault.strategies.conflict.factory import get_conflict_judge
from context_vault.utils.timeutil import utc_now_iso


@dataclass
class ConflictRecord:
    id: str
    fact_a: str
    fact_b: str
    contradict: bool
    reason: str
    created_at: str
    doc_id_a: str = ""
    doc_id_b: str = ""
    query: str = ""
    chunk_id_a: str = ""
    chunk_id_b: str = ""


def _conflicts_path(path: Path | str | None = None) -> Path:
    return Path(path or config.DEFAULT_CONFLICTS_PATH)


def load_conflicts(path: Path | str | None = None) -> list[dict[str, Any]]:
    p = _conflicts_path(path)
    if not p.is_file():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return list(data.get("conflicts") or [])
    if isinstance(data, list):
        return data
    return []


def save_conflicts(records: list[dict[str, Any]], path: Path | str | None = None) -> Path:
    p = _conflicts_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"conflicts": records, "updated_at": utc_now_iso()}
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


def flag_conflict(
    fact_a: str,
    fact_b: str,
    *,
    contradict: bool = True,
    reason: str = "",
    doc_id_a: str = "",
    doc_id_b: str = "",
    query: str = "",
    chunk_id_a: str = "",
    chunk_id_b: str = "",
    path: Path | str | None = None,
    ask_llm: bool = False,
    judge: str | None = None,
) -> ConflictRecord:
    """
    Persist a conflict record (JSON file).

    If ask_llm=True, configured ConflictJudgeStrategy decides contradict/reason.
    """
    if ask_llm:
        verdict = get_conflict_judge(judge).judge(fact_a, fact_b)
        contradict = bool(verdict["contradict"])
        reason = str(verdict["reason"])

    record = ConflictRecord(
        id=str(uuid.uuid4()),
        fact_a=fact_a,
        fact_b=fact_b,
        contradict=contradict,
        reason=reason or ("flagged manually" if contradict else "no contradiction"),
        created_at=utc_now_iso(),
        doc_id_a=doc_id_a,
        doc_id_b=doc_id_b,
        query=query,
        chunk_id_a=chunk_id_a,
        chunk_id_b=chunk_id_b,
    )

    records = load_conflicts(path)
    records.append(asdict(record))
    save_conflicts(records, path)
    return record


def mark_stale(
    doc_id: str,
    *,
    chroma_dir: Path | str | None = None,
    collection_name: str | None = None,
) -> dict[str, Any]:
    """Set status=stale on every chunk for doc_id (explicit override)."""
    collection = get_collection(chroma_dir, collection_name)
    n = set_status_for_doc(
        collection,
        doc_id,
        "stale",
        extra={"marked_stale_at": utc_now_iso()},
    )
    return {"doc_id": doc_id, "chunks_updated": n, "status": "stale"}


def _chunk_id(hit: ContextHit) -> str:
    return f"{hit.doc_id}__{hit.chunk_index}"


def candidate_pairs(
    hits: list[ContextHit], *, max_pairs: int | None = None
) -> list[tuple[ContextHit, ContextHit]]:
    """
    Pair *different* doc_ids using the earliest chunk per doc.
    Caps pairs to avoid burning Gemini quota.
    """
    max_pairs = max_pairs if max_pairs is not None else config.MAX_CONFLICT_PAIRS
    best_by_doc: dict[str, ContextHit] = {}
    for h in hits:
        if not h.doc_id:
            continue
        prev = best_by_doc.get(h.doc_id)
        if prev is None or h.chunk_index < prev.chunk_index:
            best_by_doc[h.doc_id] = h
    unique = list(best_by_doc.values())

    pairs: list[tuple[ContextHit, ContextHit]] = []
    for i, a in enumerate(unique):
        for b in unique[i + 1 :]:
            pairs.append((a, b))
            if len(pairs) >= max_pairs:
                return pairs
    return pairs


def detect_conflicts(
    query: str,
    *,
    top_k: int | None = None,
    chroma_dir: Path | str | None = None,
    collection_name: str | None = None,
    conflicts_path: Path | str | None = None,
    mark_contested: bool = True,
    judge: str | None = None,
) -> dict[str, Any]:
    """
    Retrieve → pair different docs → conflict judge → store + optional contested stamp.
    """
    hits = get_context(
        query,
        top_k=top_k,
        chroma_dir=chroma_dir,
        collection_name=collection_name,
    )
    pairs = candidate_pairs(hits)
    judge_impl = get_conflict_judge(judge)
    findings: list[dict[str, Any]] = []
    contested_ids: list[str] = []

    for a, b in pairs:
        verdict = judge_impl.judge(a.text, b.text)
        record = flag_conflict(
            a.text,
            b.text,
            contradict=verdict["contradict"],
            reason=verdict["reason"],
            doc_id_a=a.doc_id,
            doc_id_b=b.doc_id,
            query=query,
            chunk_id_a=_chunk_id(a),
            chunk_id_b=_chunk_id(b),
            path=conflicts_path,
            ask_llm=False,
        )
        entry = {
            "conflict_id": record.id,
            "doc_id_a": a.doc_id,
            "doc_id_b": b.doc_id,
            "contradict": record.contradict,
            "reason": record.reason,
            "judge": judge_impl.name,
            "preview_a": a.text.replace("\n", " ")[:100],
            "preview_b": b.text.replace("\n", " ")[:100],
        }
        findings.append(entry)
        if record.contradict:
            contested_ids.extend([_chunk_id(a), _chunk_id(b)])

    marked = 0
    if mark_contested and contested_ids:
        unique = list(dict.fromkeys(contested_ids))
        collection = get_collection(chroma_dir, collection_name)
        marked = set_status_for_ids(
            collection,
            unique,
            "contested",
            extra={"contested_at": utc_now_iso()},
        )

    return {
        "query": query,
        "hits": len(hits),
        "pairs_checked": len(pairs),
        "conflicts_found": sum(1 for f in findings if f["contradict"]),
        "chunks_marked_contested": marked,
        "judge": judge_impl.name,
        "findings": findings,
    }

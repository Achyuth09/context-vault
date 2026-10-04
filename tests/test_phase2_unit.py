"""Unit tests for Phase 2 helpers (no Gemini / Chroma required)."""

import json
from pathlib import Path

from context_vault.conflicts import candidate_pairs, flag_conflict, load_conflicts
from context_vault.get_context import ContextHit
from context_vault.gemini_judge import _parse_judge_json


def _hit(doc_id: str, text: str = "x", idx: int = 0) -> ContextHit:
    return ContextHit(
        text=text,
        doc_id=doc_id,
        source_path="/tmp/" + doc_id,
        chunk_index=idx,
        updated_at="",
        ingested_at="",
        status="fresh",
        age_days=None,
        age_bucket="unknown",
        distance=0.1,
    )


def test_candidate_pairs_different_docs_only():
    hits = [_hit("a", idx=1), _hit("a", idx=0), _hit("b"), _hit("c")]
    pairs = candidate_pairs(hits, max_pairs=10)
    # One chunk per doc → a-b, a-c, b-c; prefer earliest chunk_index for a
    assert all(p[0].doc_id != p[1].doc_id for p in pairs)
    assert len(pairs) == 3
    assert pairs[0][0].chunk_index == 0


def test_candidate_pairs_cap():
    hits = [_hit("a"), _hit("b"), _hit("c"), _hit("d")]
    pairs = candidate_pairs(hits, max_pairs=2)
    assert len(pairs) == 2


def test_parse_judge_json_plain():
    raw = '{"contradict": true, "reason": "v2 vs v3"}'
    assert _parse_judge_json(raw) == {"contradict": True, "reason": "v2 vs v3"}


def test_parse_judge_json_fenced():
    raw = '```json\n{"contradict": false, "reason": "same fact"}\n```'
    out = _parse_judge_json(raw)
    assert out["contradict"] is False
    assert "same" in out["reason"]


def test_flag_conflict_persists(tmp_path: Path):
    path = tmp_path / "conflicts.json"
    rec = flag_conflict(
        "API is v2",
        "API is v3",
        contradict=True,
        reason="version mismatch",
        doc_id_a="api_version_jan",
        doc_id_b="api_version_sep",
        path=path,
    )
    assert rec.contradict is True
    loaded = load_conflicts(path)
    assert len(loaded) == 1
    assert loaded[0]["doc_id_a"] == "api_version_jan"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "updated_at" in data

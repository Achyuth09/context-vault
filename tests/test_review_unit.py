"""Unit tests for PR review guardrail (heuristic; no LLM required)."""

from pathlib import Path

from context_vault.review import paths_from_diff, review_diff
from context_vault.strategies.review._common import parse_findings_json
from context_vault.strategies.review.factory import get_review_judge
from context_vault.strategies.review.heuristic_review import HeuristicReviewJudge

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "fixtures" / "sample_pr.diff"


def test_paths_from_diff():
    diff = SAMPLE.read_text(encoding="utf-8")
    paths = paths_from_diff(diff)
    assert any(p.endswith("users.py") for p in paths)
    assert any(p.endswith(".env") for p in paths)


def test_heuristic_flags_sample_pr():
    diff = SAMPLE.read_text(encoding="utf-8")
    findings = HeuristicReviewJudge().review(diff=diff, policies=[])
    rules = {f["rule"] for f in findings}
    assert "HARDCODED_SECRET" in rules or "API_KEY_IN_SOURCE" in rules
    assert "RAW_SQL_CONCAT" in rules
    assert "AUTH_JWT_REQUIRED" in rules or "RBAC_FROM_CLIENT" in rules
    assert "NO_SECRETS_IN_REPO" in rules


def test_parse_findings_json():
    raw = '{"findings":[{"severity":"high","rule":"X","evidence":"e","suggestion":"s"}]}'
    out = parse_findings_json(raw)
    assert out[0]["rule"] == "X"


def test_factory_aliases():
    assert get_review_judge("heuristic").name == "heuristic"
    assert get_review_judge("qwen").name == "qwen"


def test_review_diff_heuristic_end_to_end():
    """Needs ingested index; still works with empty policies if index empty."""
    diff = SAMPLE.read_text(encoding="utf-8")
    summary = review_diff(diff, provider="heuristic", title="Bad auth PR")
    assert summary["provider_used"] == "heuristic"
    assert summary["findings_count"] >= 3

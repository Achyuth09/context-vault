"""Strategy unit tests (no Gemini / Chroma required)."""

from context_vault.strategies.chunking.by_heading import ByHeadingChunking
from context_vault.strategies.chunking.by_paragraph import ByParagraphChunking
from context_vault.strategies.chunking.factory import get_chunking_strategy
from context_vault.strategies.chunking.fixed import FixedSizeChunking
from context_vault.strategies.conflict.factory import get_conflict_judge
from context_vault.strategies.conflict.heuristic import HeuristicConflictJudge
from context_vault.strategies.retrieval.factory import get_retrieval_strategy


def test_fixed_chunking_from_factory():
    s = get_chunking_strategy("fixed", chunk_size=100, overlap=20)
    assert s.name == "fixed"
    chunks = s.chunk("a" * 250)
    assert len(chunks) >= 2
    assert all(len(c) <= 100 for c in chunks)


def test_by_heading_splits_sections():
    text = "# One\n\nhello\n\n# Two\n\nworld"
    chunks = ByHeadingChunking(chunk_size=400, overlap=20).chunk(text)
    assert len(chunks) >= 2
    assert any("One" in c for c in chunks)
    assert any("Two" in c for c in chunks)


def test_by_paragraph_packs():
    text = "para one.\n\npara two.\n\npara three."
    chunks = ByParagraphChunking(chunk_size=80, overlap=10).chunk(text)
    assert len(chunks) >= 1
    assert "para one" in chunks[0]


def test_heuristic_detects_version_conflict():
    j = HeuristicConflictJudge()
    out = j.judge("API is v2", "API is now v3")
    assert out["contradict"] is True


def test_heuristic_detects_price_conflict():
    j = HeuristicConflictJudge()
    out = j.judge("Starter is $9 / month", "Starter is now $29 / month")
    assert out["contradict"] is True


def test_heuristic_no_conflict_unrelated():
    j = HeuristicConflictJudge()
    out = j.judge("Primary region is us-east-1", "On-call is Alex")
    assert out["contradict"] is False


def test_factories_default_names():
    assert get_chunking_strategy("fixed").name == "fixed"
    assert get_retrieval_strategy("similarity").name == "similarity"
    assert get_conflict_judge("heuristic").name == "heuristic"


def test_unknown_strategy_raises():
    try:
        get_chunking_strategy("nope")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "CHUNK_STRATEGY" in str(e)

"""Smoke tests for chunking + age buckets (no Chroma download required)."""

from context_vault.chunking import chunk_text
from context_vault.get_context import age_bucket
from datetime import datetime, timezone, timedelta


def test_chunk_overlap():
    text = "a" * 500
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) >= 5
    assert all(len(c) <= 100 for c in chunks)


def test_age_buckets():
    now = datetime(2026, 9, 12, tzinfo=timezone.utc)
    fresh = (now - timedelta(days=5)).isoformat()
    aging = (now - timedelta(days=45)).isoformat()
    stale = (now - timedelta(days=120)).isoformat()

    assert age_bucket(fresh, now)[1] == "fresh"
    assert age_bucket(aging, now)[1] == "aging"
    assert age_bucket(stale, now)[1] == "stale"

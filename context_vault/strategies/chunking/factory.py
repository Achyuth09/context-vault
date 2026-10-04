"""Build ChunkingStrategy from config."""

from __future__ import annotations

from context_vault import config
from context_vault.strategies.base import ChunkingStrategy
from context_vault.strategies.chunking.by_heading import ByHeadingChunking
from context_vault.strategies.chunking.by_paragraph import ByParagraphChunking
from context_vault.strategies.chunking.fixed import FixedSizeChunking

_REGISTRY: dict[str, type] = {
    "fixed": FixedSizeChunking,
    "by_heading": ByHeadingChunking,
    "by_paragraph": ByParagraphChunking,
}


def get_chunking_strategy(
    name: str | None = None,
    *,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> ChunkingStrategy:
    key = (name or config.CHUNK_STRATEGY).strip().lower()
    cls = _REGISTRY.get(key)
    if cls is None:
        known = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown CHUNK_STRATEGY={key!r}. Choose: {known}")
    return cls(chunk_size=chunk_size, overlap=overlap)

"""Character-window chunking — compat shim over ChunkingStrategy factory."""

from __future__ import annotations

from context_vault import config
from context_vault.strategies.chunking.factory import get_chunking_strategy
from context_vault.strategies.chunking.fixed import FixedSizeChunking


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[str]:
    """
    Split text using the configured chunking strategy.

    Defaults come from config (CHUNK_STRATEGY / CHUNK_SIZE / CHUNK_OVERLAP).
    Passing chunk_size/overlap forces FixedSizeChunking for backward-compatible tests.
    """
    if chunk_size is not None or overlap is not None:
        size = config.CHUNK_SIZE if chunk_size is None else chunk_size
        ov = config.CHUNK_OVERLAP if overlap is None else overlap
        return FixedSizeChunking(size, ov).chunk(text)
    return get_chunking_strategy().chunk(text)

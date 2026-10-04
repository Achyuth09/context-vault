"""Fixed-size overlapping character windows."""

from __future__ import annotations

from context_vault import config


class FixedSizeChunking:
    name = "fixed"

    def __init__(
        self,
        chunk_size: int | None = None,
        overlap: int | None = None,
    ) -> None:
        self.chunk_size = config.CHUNK_SIZE if chunk_size is None else chunk_size
        self.overlap = config.CHUNK_OVERLAP if overlap is None else overlap

    def chunk(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            piece = text[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= len(text):
                break
            start = end - self.overlap
        return chunks

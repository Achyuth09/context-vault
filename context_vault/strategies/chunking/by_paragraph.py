"""Split on blank lines; pack paragraphs up to chunk_size."""

from __future__ import annotations

import re

from context_vault import config
from context_vault.strategies.chunking.fixed import FixedSizeChunking


class ByParagraphChunking:
    name = "by_paragraph"

    def __init__(
        self,
        chunk_size: int | None = None,
        overlap: int | None = None,
    ) -> None:
        self.chunk_size = config.CHUNK_SIZE if chunk_size is None else chunk_size
        self.overlap = config.CHUNK_OVERLAP if overlap is None else overlap
        self._fallback = FixedSizeChunking(self.chunk_size, self.overlap)

    def chunk(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []

        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not paras:
            return self._fallback.chunk(text)

        chunks: list[str] = []
        current = ""
        for para in paras:
            if len(para) > self.chunk_size:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(self._fallback.chunk(para))
                continue
            candidate = f"{current}\n\n{para}".strip() if current else para
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = para
        if current:
            chunks.append(current)
        return chunks

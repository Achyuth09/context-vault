"""Split markdown on headings; pack oversized sections with fixed windows."""

from __future__ import annotations

import re

from context_vault import config
from context_vault.strategies.chunking.fixed import FixedSizeChunking

_HEADING = re.compile(r"(?m)^(#{1,6}\s+.+)$")


class ByHeadingChunking:
    name = "by_heading"

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

        parts = _HEADING.split(text)
        # parts alternate: preamble, heading, body, heading, body, ...
        sections: list[str] = []
        buf = parts[0].strip() if parts else ""
        i = 1
        while i < len(parts):
            heading = parts[i].strip()
            body = parts[i + 1].strip() if i + 1 < len(parts) else ""
            section = f"{heading}\n\n{body}".strip() if body else heading
            if buf:
                sections.append(buf)
                buf = ""
            if section:
                sections.append(section)
            i += 2
        if buf:
            sections.append(buf)

        if not sections:
            return self._fallback.chunk(text)

        out: list[str] = []
        for sec in sections:
            if len(sec) <= self.chunk_size:
                out.append(sec)
            else:
                out.extend(self._fallback.chunk(sec))
        return out

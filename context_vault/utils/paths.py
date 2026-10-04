"""Doc discovery and stable doc_id helpers."""

from __future__ import annotations

from pathlib import Path

SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt"}


def discover_docs(docs_dir: Path) -> list[Path]:
    if not docs_dir.is_dir():
        raise FileNotFoundError(f"Docs directory not found: {docs_dir}")
    return sorted(
        p
        for p in docs_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
    )


def doc_id_for(path: Path, docs_dir: Path) -> str:
    """
    Stable id from path relative to docs root (avoids stem collisions
    when two folders share the same filename).
    """
    rel = path.resolve().relative_to(docs_dir.resolve())
    return rel.with_suffix("").as_posix().replace("/", "__")

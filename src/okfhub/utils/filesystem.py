"""Filesystem helpers for project operations."""

import hashlib
from pathlib import Path


def ensure_dir(path: Path) -> None:
    """Create a directory tree if it does not exist."""

    path.mkdir(parents=True, exist_ok=True)


def sha256_text(value: str) -> str:
    """Return SHA-256 digest for stable chunk IDs and checksums."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def list_markdown_files(root: Path) -> list[Path]:
    """List all markdown files recursively under root."""

    return sorted(p for p in root.rglob("*.md") if p.is_file())

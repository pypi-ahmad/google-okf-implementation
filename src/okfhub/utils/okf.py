"""OKF-specific path and metadata helpers."""

from datetime import datetime, timezone
from pathlib import Path

from slugify import slugify


def iso_now() -> str:
    """Return current timestamp in ISO format with UTC timezone."""

    return datetime.now(timezone.utc).isoformat()


def concept_slug(title: str) -> str:
    """Create stable filename-safe slug for concept titles."""

    return slugify(title, lowercase=True, separator="-", max_length=80) or "untitled"


def concept_id_from_path(root: Path, concept_path: Path) -> str:
    """Generate deterministic concept ID from OKF relative path."""

    rel = concept_path.relative_to(root).as_posix()
    if rel.endswith(".md"):
        rel = rel[:-3]
    return rel

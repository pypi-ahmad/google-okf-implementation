"""Text parsing and chunking helpers."""

import re
from collections.abc import Iterable

LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def chunk_text(text: str, max_chars: int, overlap_chars: int) -> Iterable[str]:
    """Chunk text with overlap to preserve context.

    Args:
        text: Input text.
        max_chars: Max characters per chunk.
        overlap_chars: Overlap between adjacent chunks.

    Yields:
        Text chunks.

    Example:
        >>> list(chunk_text("abcdefghij", max_chars=4, overlap_chars=1))
        ['abcd', 'defg', 'ghij']
    """

    content = text.strip()
    if not content:
        return

    start = 0
    while start < len(content):
        end = min(start + max_chars, len(content))
        yield content[start:end]
        if end >= len(content):
            break
        start = max(0, end - overlap_chars)


def extract_markdown_links(text: str) -> list[str]:
    """Extract markdown links from content."""

    return [m.strip() for m in LINK_PATTERN.findall(text)]

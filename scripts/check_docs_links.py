"""Check that relative markdown links in docs/README/HANDBOOK point at real files.

Skips external links (http/https/mailto) and pure same-file anchors
(`#section`). For a link with a path, verifies the target file exists
relative to the linking file's directory.

Example:
    uv run python scripts/check_docs_links.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
BARE_PLACEHOLDER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
SCAN_ROOTS = ["README.md", "HANDBOOK.md", "docs"]


def find_markdown_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        target = repo_root / root
        if target.is_file():
            files.append(target)
        elif target.is_dir():
            files.extend(sorted(target.rglob("*.md")))
    return files


def strip_fenced_code_blocks(text: str) -> str:
    """Blank out fenced code blocks so illustrative links inside examples aren't checked."""

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    in_fence = False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("\n")
            continue
        out.append("\n" if in_fence else line)
    return "".join(out)


def check_file(md_file: Path, repo_root: Path) -> list[str]:
    errors: list[str] = []
    text = strip_fenced_code_blocks(md_file.read_text(encoding="utf-8"))

    for match in LINK_PATTERN.finditer(text):
        link = match.group(1).strip()

        if link.startswith(("http://", "https://", "mailto:", "#")):
            continue

        path_part = link.split("#", 1)[0].strip()
        if not path_part:
            continue
        if BARE_PLACEHOLDER.match(path_part):
            # A bare word with no `.` or `/` is prose like `[text](url)`
            # illustrating markdown syntax, not a real relative link.
            continue

        candidate = (
            repo_root / path_part.lstrip("/")
            if path_part.startswith("/")
            else (md_file.parent / path_part).resolve()
        )

        if not candidate.exists():
            rel = md_file.relative_to(repo_root)
            errors.append(f"{rel}: broken link -> {link}")

    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    all_errors: list[str] = []

    for md_file in find_markdown_files(repo_root):
        all_errors.extend(check_file(md_file, repo_root))

    if all_errors:
        print(f"Found {len(all_errors)} broken internal link(s):")
        for error in all_errors:
            print(f"  - {error}")
        return 1

    print("No broken internal links found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

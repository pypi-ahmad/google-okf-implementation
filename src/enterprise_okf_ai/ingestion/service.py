"""Ingestion service wrappers for enterprise document parsing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from ingest.parser import DocumentParser, ParsedDocument

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".markdown", ".txt", ".csv", ".html", ".htm"}


class IngestionService:
    """Parse enterprise documentation into normalized document objects."""

    def __init__(self, parser: DocumentParser | None = None):
        self._parser = parser or DocumentParser()

    def parse_file(self, file_path: str | Path) -> ParsedDocument:
        """Parse a single source file."""

        parsed = self._parser.parse(file_path)
        if parsed.errors:
            logger.warning("Recovered parsing file {} with {} errors", file_path, len(parsed.errors))
        return parsed

    def parse_directory(self, directory: str | Path, recursive: bool = True, fail_fast: bool = False) -> list[ParsedDocument]:
        """Parse all supported documents in a directory tree."""

        root = Path(directory)
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"Directory not found: {root}")

        iterator = root.rglob("*") if recursive else root.glob("*")
        files = sorted(
            path
            for path in iterator
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        logger.info("Discovered {} supported documents under {}", len(files), root)

        parsed_documents: list[ParsedDocument] = []
        for path in files:
            try:
                parsed_documents.append(self.parse_file(path))
            except Exception:  # noqa: BLE001
                logger.exception("Failed parsing {}", path)
                if fail_fast:
                    raise

        return parsed_documents

    def ingest(self, path: str | Path, recursive: bool = True, fail_fast: bool = False) -> list[ParsedDocument]:
        """Ingest either a file or directory into normalized parsed documents."""

        target = Path(path)
        if target.is_file():
            return [self.parse_file(target)]
        if target.is_dir():
            return self.parse_directory(target, recursive=recursive, fail_fast=fail_fast)
        raise FileNotFoundError(f"Path not found: {target}")

    def to_payload(self, documents: list[ParsedDocument]) -> dict[str, Any]:
        """Create deterministic JSON payload for inspection surfaces."""

        return {
            "document_count": len(documents),
            "documents": [document.to_dict() for document in documents],
        }

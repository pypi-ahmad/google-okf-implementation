"""Ingestion service to normalize heterogeneous enterprise sources."""

from pathlib import Path

from loguru import logger

from okfhub.models import DocumentChunk
from okfhub.settings import Settings
from okfhub.utils.filesystem import sha256_text
from okfhub.utils.text import chunk_text

from .parsers import parse_csv, parse_docx, parse_html, parse_markdown, parse_pdf

SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt", ".pdf", ".docx", ".csv", ".html", ".htm"}


class IngestionService:
    """Parse and chunk enterprise documents.

    Example:
        >>> service = IngestionService(Settings())
        >>> chunks = service.ingest_directory(Path("data/raw"))
    """

    def __init__(self, settings: Settings):
        self._settings = settings

    def ingest_directory(self, root: Path) -> list[DocumentChunk]:
        """Ingest all supported files under a directory tree."""

        files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
        logger.info("Discovered {} source files for ingestion", len(files))

        chunks: list[DocumentChunk] = []
        for file_path in sorted(files):
            chunks.extend(self.ingest_file(file_path))

        logger.info("Ingestion produced {} chunks", len(chunks))
        return chunks

    def ingest_file(self, path: Path) -> list[DocumentChunk]:
        """Ingest a single file and return chunks."""

        parser = self._resolve_parser(path)
        text = parser(path)

        chunk_list: list[DocumentChunk] = []
        for index, chunk in enumerate(
            chunk_text(
                text,
                max_chars=self._settings.max_chunk_chars,
                overlap_chars=self._settings.chunk_overlap_chars,
            )
        ):
            chunk_hash = sha256_text(f"{path.as_posix()}::{index}::{chunk}")
            doc_id = sha256_text(path.as_posix())
            chunk_list.append(
                DocumentChunk(
                    doc_id=doc_id,
                    source_path=path,
                    section="root",
                    text=chunk,
                    chunk_id=f"{doc_id}_{index}",
                    checksum=chunk_hash,
                )
            )

        return chunk_list

    def _resolve_parser(self, path: Path):
        suffix = path.suffix.lower()
        if suffix in {".md", ".markdown", ".txt"}:
            return parse_markdown
        if suffix == ".pdf":
            return parse_pdf
        if suffix == ".docx":
            return parse_docx
        if suffix == ".csv":
            return parse_csv
        if suffix in {".html", ".htm"}:
            return parse_html

        raise ValueError(f"Unsupported document extension: {suffix}")

"""File parsers for supported enterprise document types."""

from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from pypdf import PdfReader


def parse_markdown(path: Path) -> str:
    """Read markdown/plain text documents."""

    return path.read_text(encoding="utf-8", errors="ignore")


def parse_pdf(path: Path) -> str:
    """Extract text from PDF pages."""

    reader = PdfReader(str(path))
    texts: list[str] = []
    for idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        texts.append(f"\n## Page {idx + 1}\n{text}")
    return "\n".join(texts)


def parse_docx(path: Path) -> str:
    """Extract paragraphs from DOCX files."""

    doc = DocxDocument(str(path))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(parts)


def parse_csv(path: Path) -> str:
    """Render CSV into markdown-like table text for extraction quality."""

    df = pd.read_csv(path)
    return df.to_csv(index=False)


def parse_html(path: Path) -> str:
    """Extract visible text from HTML content."""

    html = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

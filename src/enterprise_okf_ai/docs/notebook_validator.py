"""Notebook validation utilities for CI and release hardening."""

from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_REQUIRED_TOPICS = [
    "problem",
    "raw-document rag",
    "okf",
    "ingestion",
    "bundle generation",
    "validation",
    "knowledge graph",
    "hybrid retrieval",
    "agent execution",
    "evaluation",
]


@dataclass(slots=True)
class NotebookValidationResult:
    """Structured notebook validation output."""

    notebook_path: Path
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize result as JSON-friendly dictionary."""

        return {
            "notebook_path": self.notebook_path.as_posix(),
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "stats": self.stats,
        }


def validate_notebook(
    notebook_path: str | Path,
    required_topics: list[str] | None = None,
    compile_code_cells: bool = True,
) -> NotebookValidationResult:
    """Validate notebook structure, content coverage, and code syntax.

    Args:
        notebook_path: Path to notebook file.
        required_topics: Optional required topic phrases.
        compile_code_cells: Whether to syntax-check code cells.

    Returns:
        Structured validation result.
    """

    path = Path(notebook_path)
    errors: list[str] = []
    warnings: list[str] = []
    stats: dict[str, int] = {}

    if not path.exists() or not path.is_file():
        return NotebookValidationResult(
            notebook_path=path,
            passed=False,
            errors=[f"Notebook not found: {path}"],
            warnings=[],
            stats={"cells_total": 0, "cells_markdown": 0, "cells_code": 0},
        )

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return NotebookValidationResult(
            notebook_path=path,
            passed=False,
            errors=[f"Invalid JSON notebook payload: {exc}"],
            warnings=[],
            stats={"cells_total": 0, "cells_markdown": 0, "cells_code": 0},
        )

    if not isinstance(payload, dict):
        return NotebookValidationResult(
            notebook_path=path,
            passed=False,
            errors=["Notebook root payload must be a JSON object."],
            warnings=[],
            stats={"cells_total": 0, "cells_markdown": 0, "cells_code": 0},
        )

    nbformat = payload.get("nbformat")
    if not isinstance(nbformat, int) or nbformat < 4:
        errors.append("Notebook must use nbformat >= 4.")

    raw_cells = payload.get("cells")
    if not isinstance(raw_cells, list):
        return NotebookValidationResult(
            notebook_path=path,
            passed=False,
            errors=errors + ["Notebook 'cells' field must be a list."],
            warnings=warnings,
            stats={"cells_total": 0, "cells_markdown": 0, "cells_code": 0},
        )

    markdown_cells: list[str] = []
    code_cells: list[str] = []
    for index, cell in enumerate(raw_cells):
        if not isinstance(cell, dict):
            errors.append(f"Cell {index} is not an object.")
            continue
        cell_type = cell.get("cell_type")
        source = _normalize_source(cell.get("source"))

        if cell_type == "markdown":
            markdown_cells.append(source)
        elif cell_type == "code":
            code_cells.append(source)
        else:
            warnings.append(f"Cell {index} has unsupported cell_type={cell_type!r}.")

    stats = {
        "cells_total": len(raw_cells),
        "cells_markdown": len(markdown_cells),
        "cells_code": len(code_cells),
    }

    if not markdown_cells:
        errors.append("Notebook contains no markdown cells.")
    if not code_cells:
        errors.append("Notebook contains no code cells.")

    required = required_topics or DEFAULT_REQUIRED_TOPICS
    all_markdown = "\n".join(markdown_cells).lower()
    for topic in required:
        if topic.lower() not in all_markdown:
            errors.append(f"Required topic missing from markdown: {topic}")

    if compile_code_cells:
        for index, code in enumerate(code_cells):
            try:
                compile(textwrap.dedent(code), f"{path.name}:cell-{index}", "exec")
            except SyntaxError as exc:
                errors.append(f"Code cell {index} syntax error: {exc}")

    passed = len(errors) == 0
    return NotebookValidationResult(
        notebook_path=path,
        passed=passed,
        errors=errors,
        warnings=warnings,
        stats=stats,
    )


def _normalize_source(source: object) -> str:
    """Normalize notebook cell source into plain text."""

    if isinstance(source, list):
        return "".join(str(item) for item in source)
    if isinstance(source, str):
        return source
    return ""

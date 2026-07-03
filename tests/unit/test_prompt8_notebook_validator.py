from __future__ import annotations

from pathlib import Path

from enterprise_okf_ai.docs import validate_notebook


def test_prompt8_notebook_validator_accepts_tutorial_notebook() -> None:
    notebook = Path("notebooks/tutorial.ipynb")
    result = validate_notebook(notebook)

    assert result.passed is True
    assert result.errors == []
    assert result.stats["cells_markdown"] > 0
    assert result.stats["cells_code"] > 0


def test_prompt8_notebook_validator_rejects_missing_required_topic(tmp_path: Path) -> None:
    notebook = tmp_path / "bad.ipynb"
    notebook.write_text(
        """
{
  "nbformat": 4,
  "nbformat_minor": 5,
  "metadata": {},
  "cells": [
    {"cell_type": "markdown", "metadata": {}, "source": ["# Minimal notebook\\n"]},
    {"cell_type": "code", "metadata": {}, "execution_count": null, "outputs": [], "source": ["x = 1\\n"]}
  ]
}
""".strip(),
        encoding="utf-8",
    )

    result = validate_notebook(notebook)
    assert result.passed is False
    assert any("Required topic missing" in item for item in result.errors)

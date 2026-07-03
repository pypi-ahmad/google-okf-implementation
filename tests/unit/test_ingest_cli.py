from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from enterprise_okf_ai.cli.main import app

runner = CliRunner()


def test_ingest_cli_outputs_structured_json_for_file(tmp_path: Path) -> None:
    source = tmp_path / "playbook.md"
    source.write_text(
        """
# Payments

Runbook for API timeout incidents.

## Escalation

Page the SRE team.
        """.strip(),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "ingest",
            str(source),
            "--chunk-size-chars",
            "220",
            "--chunk-overlap-chars",
            "20",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)

    assert payload["document_count"] == 1
    document = payload["documents"][0]
    assert document["file_type"] == "markdown"
    assert document["metadata"]["source"] == str(source)
    assert len(document["chunks"]) > 0


def test_ingest_cli_outputs_structured_json_for_directory(tmp_path: Path) -> None:
    source_dir = tmp_path / "raw"
    source_dir.mkdir()

    (source_dir / "a.md").write_text("# A\n\nalpha", encoding="utf-8")
    (source_dir / "b.md").write_text("# B\n\nbeta", encoding="utf-8")

    result = runner.invoke(app, ["ingest", str(source_dir)])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)

    assert payload["document_count"] == 2

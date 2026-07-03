from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from enterprise_okf_ai.cli.main import app

runner = CliRunner()


def test_build_okf_cli_generates_bundle_from_input_directory(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    (input_dir / "apis").mkdir(parents=True, exist_ok=True)
    (input_dir / "datasets").mkdir(parents=True, exist_ok=True)

    (input_dir / "apis" / "orders.md").write_text(
        """
# Orders API

PATCH /v1/orders updates order lifecycle state.

## Dependencies
- Customer Profile Dataset
        """.strip(),
        encoding="utf-8",
    )

    (input_dir / "datasets" / "customer_profile.md").write_text(
        """
# Customer Profile Dataset

Customer dimension with region and lifecycle metadata.
        """.strip(),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["build-okf", str(input_dir), str(output_dir)])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["concept_count"] >= 2

    assert (output_dir / "apis" / "orders-api.md").exists()
    assert (output_dir / "datasets" / "customer-profile-dataset.md").exists()
    assert (output_dir / "index.md").exists()

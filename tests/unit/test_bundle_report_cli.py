from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from enterprise_okf_ai.cli.main import app

runner = CliRunner()


def _write_okf(path: Path, frontmatter: dict[str, object], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=False).strip()
    path.write_text(f"---\n{fm}\n---\n\n{body}\n", encoding="utf-8")


def test_bundle_report_cli_outputs_summary_and_writes_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "okf"
    _write_okf(
        root / "datasets" / "orders.md",
        {
            "id": "dataset:orders",
            "type": "dataset",
            "title": "Orders",
            "description": "Orders dataset",
            "tags": ["dataset"],
            "resource": "datasets/orders.md",
            "sources": ["datasets/orders.md"],
            "relationships": [],
            "timestamp": "2026-07-03T00:00:00+00:00",
        },
        "# Orders",
    )
    _write_okf(
        root / "apis" / "orders-api.md",
        {
            "id": "api:orders-api",
            "type": "api",
            "title": "Orders API",
            "description": "Order mutations",
            "tags": ["api"],
            "resource": "apis/orders-api.md",
            "sources": ["apis/orders-api.md"],
            "relationships": [],
            "timestamp": "2026-07-03T00:00:00+00:00",
        },
        "# Orders API\n[Orders](/datasets/orders.md)",
    )

    json_out = tmp_path / "reports" / "health.json"
    md_out = tmp_path / "reports" / "health.md"

    result = runner.invoke(
        app,
        [
            "bundle-report",
            str(root),
            "--output-json",
            str(json_out),
            "--output-markdown",
            str(md_out),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["validation_passed"] is True
    assert payload["graph_stats"]["nodes"] == 2

    assert json_out.exists()
    assert md_out.exists()

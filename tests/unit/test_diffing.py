from pathlib import Path

from okfhub.diffing import OKFDiffService


def _write_doc(path: Path, title: str, concept_type: str, description: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""
---
type: {concept_type}
title: {title}
description: {description}
tags: []
resource: internal
timestamp: 2026-07-01T00:00:00Z
---

# Summary
{description}
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_diff_detects_added_removed_and_modified(tmp_path: Path) -> None:
    old_root = tmp_path / "old"
    new_root = tmp_path / "new"

    _write_doc(old_root / "apis" / "orders.md", "Orders API", "api", "v1")
    _write_doc(old_root / "metrics" / "mau.md", "MAU", "metric", "definition v1")

    _write_doc(new_root / "apis" / "orders.md", "Orders API", "api", "v2")
    _write_doc(new_root / "metrics" / "dau.md", "DAU", "metric", "definition")

    report = OKFDiffService().diff(old_root=old_root, new_root=new_root)

    assert len(report.added) == 1
    assert len(report.removed) == 1
    assert len(report.modified) == 1


def test_diff_detects_changed_metrics_and_renamed_apis(tmp_path: Path) -> None:
    old_root = tmp_path / "old"
    new_root = tmp_path / "new"

    _write_doc(old_root / "metrics" / "mau.md", "Monthly Active Users", "metric", "definition v1")
    _write_doc(old_root / "apis" / "orders-api.md", "Orders API", "api", "legacy endpoint")

    _write_doc(new_root / "metrics" / "mau.md", "Monthly Active Users", "metric", "definition v2")
    _write_doc(new_root / "apis" / "orders-service-api.md", "Orders Service API", "api", "renamed endpoint")

    report = OKFDiffService().diff(old_root=old_root, new_root=new_root)

    assert len(report.changed_metrics) == 1
    assert report.changed_metrics[0].concept_id == "metrics/mau"
    assert len(report.renamed_apis) == 1
    assert report.renamed_apis[0].old_path == "apis/orders-api.md"
    assert report.renamed_apis[0].new_path == "apis/orders-service-api.md"

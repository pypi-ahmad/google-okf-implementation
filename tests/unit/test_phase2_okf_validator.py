from pathlib import Path

from validators.okf_validator import OKFValidator


def _write_concept(path: Path, frontmatter: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8")


def test_okf_validator_reports_expected_failures(tmp_path: Path) -> None:
    root = tmp_path / "okf"

    _write_concept(
        root / "datasets" / "orders.md",
        """
type: dataset
title: Orders
description: Orders dataset
tags: [warehouse]
resource: warehouse.orders
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "# Summary\nSee [Missing](/apis/missing.md)",
    )

    _write_concept(
        root / "datasets" / "orders-duplicate.md",
        """
type: dataset
title: Orders
description: Duplicate orders dataset
tags: [warehouse]
resource: warehouse.orders.dup
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "# Summary\nNo links",
    )

    _write_concept(
        root / "apis" / "orders-api.md",
        """
type: api
title: Orders API
description: Updates orders
tags: [api]
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "# Summary\nNo links",
    )

    report = OKFValidator().validate(root)

    codes = {issue.code for issue in report.issues}
    assert "BROKEN_INTERNAL_LINK" in codes
    assert "DUPLICATE_CONCEPT_DEFINITION" in codes
    assert "MISSING_MANDATORY_FIELDS" in codes
    assert report.passed is False

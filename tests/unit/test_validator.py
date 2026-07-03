from pathlib import Path

from okfhub.validators import OKFValidator


def _write_concept(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_validator_detects_broken_links(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    _write_concept(
        bundle / "apis" / "orders.md",
        """
---
type: api
title: Orders API
description: Updates orders
tags: [orders]
resource: docs/orders
timestamp: 2026-07-01T00:00:00Z
---

# Summary
See [Missing](/datasets/missing.md)
""".strip()
        + "\n",
    )

    report = OKFValidator().validate(bundle)

    assert report.passed is False
    assert any(issue.code == "BROKEN_LINK" for issue in report.errors)


def test_validator_detects_missing_required_type(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    _write_concept(
        bundle / "metrics" / "mau.md",
        """
---
title: Monthly Active Users
description: MAU definition
tags: [growth]
resource: docs/mau
timestamp: 2026-07-01T00:00:00Z
---

# Summary
MAU concept
""".strip()
        + "\n",
    )

    report = OKFValidator().validate(bundle)

    assert any(issue.code == "MISSING_REQUIRED_TYPE" for issue in report.errors)

from __future__ import annotations

from pathlib import Path

import pytest

from enterprise_okf_ai.validators.spec_conformance import OKFSpecConformanceValidator


def test_spec_conformance_minimal_example_bundle_passes() -> None:
    report = OKFSpecConformanceValidator().validate(Path("examples/00_minimal_okf"))
    assert report.passed, report.to_dict()


def test_spec_conformance_sample_bundle_passes() -> None:
    report = OKFSpecConformanceValidator().validate(Path("examples/sample_okf_bundle"))
    assert report.passed, report.to_dict()


def test_spec_conformance_missing_frontmatter_fails(tmp_path: Path) -> None:
    (tmp_path / "index.md").write_text("# Root index\n", encoding="utf-8")
    (tmp_path / "concept.md").write_text("# Missing frontmatter\n", encoding="utf-8")

    report = OKFSpecConformanceValidator().validate(tmp_path)
    assert not report.passed
    assert any(issue.code == "MISSING_FRONTMATTER" for issue in report.issues)


def test_spec_conformance_missing_type_fails(tmp_path: Path) -> None:
    (tmp_path / "index.md").write_text("# Root index\n", encoding="utf-8")
    (tmp_path / "concept.md").write_text("---\ntitle: x\n---\n\n# Body\n", encoding="utf-8")

    report = OKFSpecConformanceValidator().validate(tmp_path)
    assert not report.passed
    assert any(issue.code == "MISSING_TYPE" for issue in report.issues)


@pytest.mark.parametrize(
    "log_text",
    [
        "# Log\n\n## 2026-13-40\n* bad\n",
        "# Log\n\n## not-a-date\n* bad\n",
        "---\nkey: value\n---\n\n# Log\n\n## 2026-07-01\n* ok\n",
    ],
)
def test_spec_conformance_invalid_log_fails(tmp_path: Path, log_text: str) -> None:
    (tmp_path / "index.md").write_text("# Root index\n", encoding="utf-8")
    (tmp_path / "log.md").write_text(log_text, encoding="utf-8")
    (tmp_path / "concept.md").write_text("---\ntype: Note\n---\n\n# Body\n", encoding="utf-8")

    report = OKFSpecConformanceValidator().validate(tmp_path)
    assert not report.passed


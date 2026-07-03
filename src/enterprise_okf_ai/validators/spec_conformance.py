"""OKF v0.1 spec conformance checks (minimal, spec-accurate).

This is intentionally separate from this repo's stricter enterprise validator
(`src/validators/okf_validator.py`), which enforces additional fields and quality gates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

_RESERVED_FILES = {"index.md", "log.md"}
_DATE_HEADING = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$")


@dataclass(slots=True)
class SpecIssue:
    severity: str  # "error" | "warning"
    code: str
    message: str
    file_path: str | None = None


@dataclass(slots=True)
class OKFSpecConformanceReport:
    okf_dir: Path
    issues: list[SpecIssue] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    @property
    def errors(self) -> list[SpecIssue]:
        """Return error-level conformance issues."""
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[SpecIssue]:
        """Return warning-level conformance issues."""
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def passed(self) -> bool:
        """Whether the bundle passed spec conformance (no errors)."""
        return len(self.errors) == 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to a JSON-friendly dictionary."""
        return {
            "passed": self.passed,
            "okf_dir": self.okf_dir.as_posix(),
            "stats": self.stats,
            "issues": [
                {
                    "severity": item.severity,
                    "code": item.code,
                    "message": item.message,
                    "file_path": item.file_path,
                }
                for item in self.issues
            ],
        }


class OKFSpecConformanceValidator:
    """Validate a bundle against the OKF v0.1 spec conformance rules.

    Spec conformance is deliberately minimal (SPEC.md §9):
    1) Every non-reserved `.md` file has a parseable YAML frontmatter block.
    2) Every frontmatter block has a non-empty `type` field.
    3) Reserved files (`index.md`, `log.md`) follow their structures when present.
    """

    def validate(self, okf_dir: str | Path) -> OKFSpecConformanceReport:
        """Validate a bundle directory against OKF v0.1 spec conformance rules."""
        root = Path(okf_dir)
        report = OKFSpecConformanceReport(okf_dir=root)

        if not root.exists() or not root.is_dir():
            report.issues.append(
                SpecIssue(
                    severity="error",
                    code="DIRECTORY_NOT_FOUND",
                    message=f"OKF directory does not exist: {root}",
                )
            )
            report.stats = {"files_scanned": 0, "concept_files": 0, "index_files": 0, "log_files": 0, "errors": 1, "warnings": 0}
            return report

        md_files = sorted(path for path in root.rglob("*.md") if path.is_file())

        concept_files = 0
        index_files = 0
        log_files = 0

        for path in md_files:
            rel = path.relative_to(root).as_posix()
            name = path.name.lower()

            if name == "index.md":
                index_files += 1
                self._check_index_md(root=root, path=path, rel=rel, report=report)
                continue
            if name == "log.md":
                log_files += 1
                self._check_log_md(path=path, rel=rel, report=report)
                continue

            # Any other `.md` is a concept document under the spec.
            concept_files += 1
            self._check_concept_md(path=path, rel=rel, report=report)

        report.stats = {
            "files_scanned": len(md_files),
            "concept_files": concept_files,
            "index_files": index_files,
            "log_files": log_files,
            "errors": len(report.errors),
            "warnings": len(report.warnings),
        }
        return report

    def _check_index_md(self, root: Path, path: Path, rel: str, report: OKFSpecConformanceReport) -> None:
        text = path.read_text(encoding="utf-8", errors="replace")
        is_root_index = path.parent == root

        if not text.startswith("---\n"):
            return

        if not is_root_index:
            report.issues.append(
                SpecIssue(
                    severity="error",
                    code="INDEX_FRONTMATTER_NOT_ALLOWED",
                    message="Frontmatter is only permitted in the bundle-root index.md.",
                    file_path=rel,
                )
            )
            return

        frontmatter = self._parse_frontmatter_block(text=text, rel=rel, report=report)
        if frontmatter is None:
            return

        okf_version = frontmatter.get("okf_version")
        if not isinstance(okf_version, str) or not okf_version.strip():
            report.issues.append(
                SpecIssue(
                    severity="error",
                    code="ROOT_INDEX_MISSING_OKF_VERSION",
                    message='Bundle-root index.md frontmatter must include a non-empty `okf_version` string.',
                    file_path=rel,
                )
            )
            return

        if okf_version.strip() != "0.1":
            report.issues.append(
                SpecIssue(
                    severity="warning",
                    code="UNKNOWN_OKF_VERSION",
                    message=f'Bundle declares okf_version={okf_version!r}; this validator targets OKF v0.1.',
                    file_path=rel,
                )
            )

    def _check_log_md(self, path: Path, rel: str, report: OKFSpecConformanceReport) -> None:
        text = path.read_text(encoding="utf-8", errors="replace")
        if text.startswith("---\n"):
            report.issues.append(
                SpecIssue(
                    severity="error",
                    code="LOG_FRONTMATTER_NOT_ALLOWED",
                    message="log.md must not include frontmatter.",
                    file_path=rel,
                )
            )
            return

        headings: list[str] = []
        for line in text.splitlines():
            match = _DATE_HEADING.match(line)
            if match:
                headings.append(match.group(1))
            elif line.startswith("## "):
                report.issues.append(
                    SpecIssue(
                        severity="error",
                        code="LOG_INVALID_DATE_HEADING",
                        message="log.md date headings must be ISO 8601 `YYYY-MM-DD` (e.g. `## 2026-05-15`).",
                        file_path=rel,
                    )
                )
                return

        if not headings:
            report.issues.append(
                SpecIssue(
                    severity="error",
                    code="LOG_MISSING_DATE_HEADINGS",
                    message="log.md must include at least one `## YYYY-MM-DD` date heading.",
                    file_path=rel,
                )
            )
            return

        for heading in headings:
            try:
                date.fromisoformat(heading)
            except ValueError:
                report.issues.append(
                    SpecIssue(
                        severity="error",
                        code="LOG_INVALID_DATE_VALUE",
                        message=f"Invalid log.md date heading: {heading!r}",
                        file_path=rel,
                    )
                )
                return

    def _check_concept_md(self, path: Path, rel: str, report: OKFSpecConformanceReport) -> None:
        text = path.read_text(encoding="utf-8", errors="replace")
        frontmatter = self._parse_frontmatter_block(text=text, rel=rel, report=report)
        if frontmatter is None:
            return

        type_value = frontmatter.get("type")
        if not isinstance(type_value, str) or not type_value.strip():
            report.issues.append(
                SpecIssue(
                    severity="error",
                    code="MISSING_TYPE",
                    message="Concept frontmatter must include a non-empty `type` field.",
                    file_path=rel,
                )
            )

    def _parse_frontmatter_block(self, text: str, rel: str, report: OKFSpecConformanceReport) -> dict[str, Any] | None:
        if not text.startswith("---\n"):
            report.issues.append(
                SpecIssue(
                    severity="error",
                    code="MISSING_FRONTMATTER",
                    message="Missing YAML frontmatter block (must start with `---`).",
                    file_path=rel,
                )
            )
            return None

        lines = text.splitlines()
        end_idx: int | None = None
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                end_idx = idx
                break

        if end_idx is None:
            report.issues.append(
                SpecIssue(
                    severity="error",
                    code="FRONTMATTER_NOT_CLOSED",
                    message="Frontmatter block must be closed with a second `---` line.",
                    file_path=rel,
                )
            )
            return None

        yaml_text = "\n".join(lines[1:end_idx]).strip()
        try:
            data = yaml.safe_load(yaml_text) if yaml_text else {}
        except yaml.YAMLError as exc:
            report.issues.append(
                SpecIssue(
                    severity="error",
                    code="FRONTMATTER_YAML_PARSE_ERROR",
                    message=f"Frontmatter YAML parse error: {exc}",
                    file_path=rel,
                )
            )
            return None

        if not isinstance(data, dict):
            report.issues.append(
                SpecIssue(
                    severity="error",
                    code="FRONTMATTER_NOT_MAPPING",
                    message="Frontmatter YAML must parse to a mapping (key/value object).",
                    file_path=rel,
                )
            )
            return None

        return data

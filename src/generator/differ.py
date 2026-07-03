"""Knowledge diff engine for comparing OKF directory versions."""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz import fuzz

RESERVED_FILES = {"index.md", "log.md"}


@dataclass(slots=True)
class ConceptFile:
    """Parsed OKF concept file."""

    rel_path: str
    frontmatter: dict[str, Any]
    body: str


@dataclass(slots=True)
class DiffSummary:
    """Structured summary for OKF version diffs."""

    added_files: list[str] = field(default_factory=list)
    removed_files: list[str] = field(default_factory=list)
    changed_metrics: list[str] = field(default_factory=list)
    renamed_apis: list[str] = field(default_factory=list)
    updated_schemas: list[str] = field(default_factory=list)


class OKFDiffer:
    """Compare two OKF versions and emit structured markdown diff."""

    def compare(self, v1_dir: str | Path, v2_dir: str | Path) -> DiffSummary:
        """Compute structured diff between two OKF directory snapshots."""

        old_docs = self._load_docs(Path(v1_dir))
        new_docs = self._load_docs(Path(v2_dir))

        old_paths = set(old_docs)
        new_paths = set(new_docs)

        summary = DiffSummary(
            added_files=sorted(new_paths - old_paths),
            removed_files=sorted(old_paths - new_paths),
        )

        for rel_path in sorted(old_paths & new_paths):
            old = old_docs[rel_path]
            new = new_docs[rel_path]

            if not self._is_changed(old, new):
                continue

            concept_type = str(new.frontmatter.get("type", "")).lower()
            if concept_type == "metric":
                summary.changed_metrics.append(rel_path)
            if concept_type in {"dataset", "table"}:
                summary.updated_schemas.append(rel_path)

        summary.renamed_apis = self._detect_renamed_apis(
            old_docs=old_docs,
            new_docs=new_docs,
            removed=summary.removed_files,
            added=summary.added_files,
        )
        return summary

    def to_markdown(self, summary: DiffSummary, v1_label: str = "v1", v2_label: str = "v2") -> str:
        """Render human-readable markdown diff from structured summary."""

        lines = [
            f"# OKF Diff Report: {v1_label} -> {v2_label}",
            "",
            "## Added Files",
            *self._render_list(summary.added_files),
            "",
            "## Removed Files",
            *self._render_list(summary.removed_files),
            "",
            "## Changed Metrics",
            *self._render_list(summary.changed_metrics),
            "",
            "## Renamed APIs",
            *self._render_list(summary.renamed_apis),
            "",
            "## Updated Schemas",
            *self._render_list(summary.updated_schemas),
            "",
        ]
        return "\n".join(lines)

    def save_markdown(self, summary: DiffSummary, output_path: str | Path, v1_label: str = "v1", v2_label: str = "v2") -> Path:
        """Save markdown diff report to disk."""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown(summary, v1_label=v1_label, v2_label=v2_label), encoding="utf-8")
        return path

    def unified_body_diff(self, old_file: str | Path, new_file: str | Path) -> str:
        """Return unified textual diff between two OKF markdown files."""

        old_lines = Path(old_file).read_text(encoding="utf-8", errors="ignore").splitlines()
        new_lines = Path(new_file).read_text(encoding="utf-8", errors="ignore").splitlines()

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=str(old_file),
            tofile=str(new_file),
            lineterm="",
        )
        return "\n".join(diff)

    def _load_docs(self, root: Path) -> dict[str, ConceptFile]:
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"OKF directory not found: {root}")

        docs: dict[str, ConceptFile] = {}
        for path in sorted(root.rglob("*.md")):
            if not path.is_file() or path.name in RESERVED_FILES:
                continue

            frontmatter, body = self._parse_frontmatter(path)
            rel_path = path.resolve().relative_to(root.resolve()).as_posix()
            docs[rel_path] = ConceptFile(rel_path=rel_path, frontmatter=frontmatter, body=body)

        return docs

    def _parse_frontmatter(self, path: Path) -> tuple[dict[str, Any], str]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()

        if not lines or lines[0].strip() != "---":
            return {}, text

        end_idx = None
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                end_idx = idx
                break

        if end_idx is None:
            return {}, text

        fm_text = "\n".join(lines[1:end_idx])
        body = "\n".join(lines[end_idx + 1 :]).strip()

        try:
            frontmatter = yaml.safe_load(fm_text) or {}
        except yaml.YAMLError:
            frontmatter = {}

        if not isinstance(frontmatter, dict):
            frontmatter = {}

        return frontmatter, body

    def _is_changed(self, old: ConceptFile, new: ConceptFile) -> bool:
        return old.frontmatter != new.frontmatter or old.body.strip() != new.body.strip()

    def _detect_renamed_apis(
        self,
        old_docs: dict[str, ConceptFile],
        new_docs: dict[str, ConceptFile],
        removed: list[str],
        added: list[str],
    ) -> list[str]:
        candidates: list[str] = []
        consumed_added: set[str] = set()

        for old_path in removed:
            old_doc = old_docs.get(old_path)
            if old_doc is None:
                continue
            if str(old_doc.frontmatter.get("type", "")).lower() != "api":
                continue

            old_title = str(old_doc.frontmatter.get("title", old_path))
            old_resource = str(old_doc.frontmatter.get("resource", ""))

            best_score = 0
            best_path = None
            for new_path in added:
                if new_path in consumed_added:
                    continue

                new_doc = new_docs.get(new_path)
                if new_doc is None:
                    continue
                if str(new_doc.frontmatter.get("type", "")).lower() != "api":
                    continue

                title_score = fuzz.ratio(old_title.lower(), str(new_doc.frontmatter.get("title", "")).lower())
                resource_score = fuzz.ratio(old_resource.lower(), str(new_doc.frontmatter.get("resource", "")).lower())
                score = max(title_score, resource_score)

                if score > best_score:
                    best_score = score
                    best_path = new_path

            if best_path is not None and best_score >= 80:
                consumed_added.add(best_path)
                candidates.append(f"{old_path} -> {best_path} (similarity={best_score})")

        return sorted(candidates)

    def _render_list(self, items: list[str]) -> list[str]:
        if not items:
            return ["- None"]
        return [f"- {item}" for item in items]

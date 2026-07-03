"""Strict OKF bundle validator for structural and referential integrity."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx
import yaml

MANDATORY_FIELDS = [
    "id",
    "type",
    "title",
    "description",
    "tags",
    "resource",
    "sources",
    "relationships",
    "timestamp",
]
# OKF v0.1 reserves only `index.md` and `log.md` (SPEC.md §3.1).
# All other `.md` files are concept documents, including `README.md`.
RESERVED_FILES = {"index.md", "log.md"}
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


@dataclass(slots=True)
class DiagnosticIssue:
    """Single validator diagnostic item."""

    severity: str
    code: str
    message: str
    file_path: str | None = None


@dataclass(slots=True)
class ParsedDocument:
    """Internal representation of one OKF markdown document."""

    path: Path
    relative_path: str
    frontmatter: dict[str, Any]
    body: str
    markdown_links: list[str]
    relationship_links: list[str]


@dataclass(slots=True)
class ValidationReport:
    """Validation report with diagnostics and aggregate stats."""

    issues: list[DiagnosticIssue] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    @property
    def errors(self) -> list[DiagnosticIssue]:
        """Return error-level diagnostics."""
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[DiagnosticIssue]:
        """Return warning-level diagnostics."""
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def passed(self) -> bool:
        """Whether validation passed without errors."""
        return len(self.errors) == 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to plain dictionary."""

        return {
            "passed": self.passed,
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


class OKFValidator:
    """Validate OKF directories for metadata and link integrity."""

    def __init__(self, mandatory_fields: list[str] | None = None):
        self._mandatory_fields = mandatory_fields or MANDATORY_FIELDS

    def validate(self, okf_dir: str | Path) -> ValidationReport:
        """Run validation checks on an OKF bundle directory."""

        root = Path(okf_dir)
        report = ValidationReport()

        if not root.exists() or not root.is_dir():
            report.issues.append(
                DiagnosticIssue(
                    severity="error",
                    code="DIRECTORY_NOT_FOUND",
                    message=f"OKF directory does not exist: {root}",
                )
            )
            report.stats = {
                "files_scanned": 0,
                "documents_parsed": 0,
                "edges": 0,
                "cycles": 0,
                "orphans": 0,
                "duplicate_concepts": 0,
                "broken_links": 0,
            }
            return report

        files = sorted(path for path in root.rglob("*.md") if path.is_file() and path.name.lower() not in RESERVED_FILES)
        parsed_docs: list[ParsedDocument] = []

        for file_path in files:
            parsed = self._parse_markdown_document(root=root, file_path=file_path, issues=report.issues)
            if parsed is None:
                continue
            parsed_docs.append(parsed)

        self._check_mandatory_fields(parsed_docs, report.issues)
        duplicate_count = self._check_duplicates(parsed_docs, report.issues)

        graph = nx.DiGraph()
        for document in parsed_docs:
            graph.add_node(document.path.resolve())

        broken_links, edge_count = self._check_links(parsed_docs, root=root, issues=report.issues, graph=graph)
        orphan_count = self._check_orphans(parsed_docs, issues=report.issues, graph=graph)
        cycle_count = self._check_cycles(parsed_docs, issues=report.issues, graph=graph)

        report.stats = {
            "files_scanned": len(files),
            "documents_parsed": len(parsed_docs),
            "errors": len(report.errors),
            "warnings": len(report.warnings),
            "edges": edge_count,
            "cycles": cycle_count,
            "orphans": orphan_count,
            "duplicate_concepts": duplicate_count,
            "broken_links": broken_links,
        }
        return report

    def _parse_markdown_document(
        self,
        root: Path,
        file_path: Path,
        issues: list[DiagnosticIssue],
    ) -> ParsedDocument | None:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()
        rel_path = self._relative(root, file_path)

        if not lines or lines[0].strip() != "---":
            issues.append(
                DiagnosticIssue(
                    severity="error",
                    code="MISSING_FRONTMATTER",
                    message="Missing YAML frontmatter opening delimiter (`---`).",
                    file_path=rel_path,
                )
            )
            return None

        end_idx = None
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                end_idx = index
                break

        if end_idx is None:
            issues.append(
                DiagnosticIssue(
                    severity="error",
                    code="INVALID_FRONTMATTER_BLOCK",
                    message="YAML frontmatter closing delimiter (`---`) not found.",
                    file_path=rel_path,
                )
            )
            return None

        frontmatter_text = "\n".join(lines[1:end_idx])
        body = "\n".join(lines[end_idx + 1 :]).strip()

        try:
            frontmatter = yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError as exc:
            issues.append(
                DiagnosticIssue(
                    severity="error",
                    code="INVALID_YAML_FRONTMATTER",
                    message=f"Failed to parse YAML frontmatter: {exc}",
                    file_path=rel_path,
                )
            )
            return None

        if not isinstance(frontmatter, dict):
            issues.append(
                DiagnosticIssue(
                    severity="error",
                    code="INVALID_YAML_OBJECT",
                    message="YAML frontmatter must deserialize to a mapping/object.",
                    file_path=rel_path,
                )
            )
            return None

        markdown_links = [match.strip() for match in LINK_PATTERN.findall(body) if match.strip()]
        relationship_links = self._extract_relationship_links(frontmatter)
        return ParsedDocument(
            path=file_path,
            relative_path=rel_path,
            frontmatter=frontmatter,
            body=body,
            markdown_links=markdown_links,
            relationship_links=relationship_links,
        )

    def _extract_relationship_links(self, frontmatter: dict[str, Any]) -> list[str]:
        raw_relationships = frontmatter.get("relationships")
        if not isinstance(raw_relationships, list):
            return []

        links: list[str] = []
        for item in raw_relationships:
            if isinstance(item, dict):
                path = item.get("path")
                if isinstance(path, str) and path.strip():
                    links.append(path.strip())
            elif isinstance(item, str) and item.strip():
                links.append(item.strip())

        return links

    def _check_mandatory_fields(self, documents: list[ParsedDocument], issues: list[DiagnosticIssue]) -> None:
        for document in documents:
            missing: list[str] = []
            for key in self._mandatory_fields:
                if key not in document.frontmatter:
                    missing.append(key)
                    continue

                value = document.frontmatter.get(key)
                if key in {"tags", "sources", "relationships"}:
                    if not isinstance(value, list):
                        missing.append(key)
                    continue

                if self._is_empty(value):
                    missing.append(key)

            if missing:
                issues.append(
                    DiagnosticIssue(
                        severity="error",
                        code="MISSING_MANDATORY_FIELDS",
                        message=f"Missing mandatory frontmatter fields: {', '.join(missing)}",
                        file_path=document.relative_path,
                    )
                )

    def _check_duplicates(self, documents: list[ParsedDocument], issues: list[DiagnosticIssue]) -> int:
        duplicates = 0

        seen_by_id: dict[str, str] = {}
        seen_by_canonical: dict[tuple[str, str], str] = {}

        for document in documents:
            concept_id = str(document.frontmatter.get("id", "")).strip().lower()
            concept_type = str(document.frontmatter.get("type", "")).strip().lower()
            title = str(document.frontmatter.get("title", "")).strip().lower()

            if concept_id:
                if concept_id in seen_by_id:
                    duplicates += 1
                    issues.append(
                        DiagnosticIssue(
                            severity="error",
                            code="DUPLICATE_CONCEPT_DEFINITION",
                            message=f"Duplicate concept id `{concept_id}` also defined in {seen_by_id[concept_id]}",
                            file_path=document.relative_path,
                        )
                    )
                else:
                    seen_by_id[concept_id] = document.relative_path

            if concept_type and title:
                signature = (concept_type, title)
                if signature in seen_by_canonical:
                    duplicates += 1
                    issues.append(
                        DiagnosticIssue(
                            severity="error",
                            code="DUPLICATE_CONCEPT_DEFINITION",
                            message=(
                                f"Duplicate concept `{concept_type}:{title}` also defined in "
                                f"{seen_by_canonical[signature]}"
                            ),
                            file_path=document.relative_path,
                        )
                    )
                else:
                    seen_by_canonical[signature] = document.relative_path

        return duplicates

    def _check_links(
        self,
        documents: list[ParsedDocument],
        root: Path,
        issues: list[DiagnosticIssue],
        graph: nx.DiGraph,
    ) -> tuple[int, int]:
        broken_links = 0
        edge_count = 0
        known_paths = {document.path.resolve() for document in documents}

        for document in documents:
            all_links = list(document.markdown_links) + list(document.relationship_links)
            for raw_link in all_links:
                target = self._resolve_internal_link(root=root, source=document.path, link=raw_link)
                if target is None:
                    continue

                resolved_target = target.resolve()
                if resolved_target not in known_paths:
                    broken_links += 1
                    issues.append(
                        DiagnosticIssue(
                            severity="error",
                            code="BROKEN_INTERNAL_LINK",
                            message=f"Broken internal link: {raw_link}",
                            file_path=document.relative_path,
                        )
                    )
                    continue

                edge_count += 1
                graph.add_edge(document.path.resolve(), resolved_target)

        return broken_links, edge_count

    def _check_orphans(
        self,
        documents: list[ParsedDocument],
        issues: list[DiagnosticIssue],
        graph: nx.DiGraph,
    ) -> int:
        orphan_count = 0

        for document in documents:
            node = document.path.resolve()
            if graph.in_degree(node) == 0 and graph.out_degree(node) == 0:
                orphan_count += 1
                issues.append(
                    DiagnosticIssue(
                        severity="warning",
                        code="ORPHAN_DOCUMENT",
                        message="Document has no inbound or outbound internal references.",
                        file_path=document.relative_path,
                    )
                )

        return orphan_count

    def _check_cycles(
        self,
        documents: list[ParsedDocument],
        issues: list[DiagnosticIssue],
        graph: nx.DiGraph,
    ) -> int:
        node_to_rel = {document.path.resolve(): document.relative_path for document in documents}
        cycle_count = 0

        for cycle in nx.simple_cycles(graph):
            if len(cycle) <= 1:
                continue
            cycle_count += 1
            cycle_path = " -> ".join(node_to_rel.get(node, str(node)) for node in cycle)
            issues.append(
                DiagnosticIssue(
                    severity="error",
                    code="CIRCULAR_REFERENCE",
                    message=f"Circular reference detected: {cycle_path}",
                )
            )

        return cycle_count

    def _resolve_internal_link(self, root: Path, source: Path, link: str) -> Path | None:
        normalized = link.strip()
        if not normalized:
            return None

        if normalized.startswith(("http://", "https://", "mailto:", "#")):
            return None

        normalized = normalized.split("#", 1)[0].split("?", 1)[0].strip()
        if not normalized:
            return None

        base_candidates = (
            [root / normalized.lstrip("/")]
            if normalized.startswith("/")
            else [source.parent / normalized, root / normalized]
        )

        try_candidates: list[Path] = []
        for candidate in base_candidates:
            try_candidates.append(candidate)
            if candidate.suffix == "":
                try_candidates.append(candidate.with_suffix(".md"))

        root_resolved = root.resolve()
        fallback: Path | None = None
        for possible in try_candidates:
            try:
                resolved = possible.resolve()
                resolved.relative_to(root_resolved)
            except ValueError:
                continue
            except OSError:
                continue

            if possible.exists() and possible.is_file():
                return possible
            if fallback is None:
                fallback = possible

        return fallback

    def _relative(self, root: Path, path: Path) -> str:
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()

    def _is_empty(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        if isinstance(value, list):
            return len(value) == 0
        return False

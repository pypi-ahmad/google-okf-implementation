"""OKF bundle validator for structural and semantic checks."""

from pathlib import Path

import frontmatter
import networkx as nx
from loguru import logger

from okfhub.models import ValidationIssue, ValidationReport
from okfhub.utils.filesystem import list_markdown_files
from okfhub.utils.okf import concept_id_from_path
from okfhub.utils.text import extract_markdown_links

RESERVED_FILENAMES = {"index.md", "log.md"}


class OKFValidator:
    """Validate OKF bundles against structural requirements.

    Example:
        >>> validator = OKFValidator()
        >>> report = validator.validate(Path("okf_bundle"))
    """

    def validate(self, root: Path) -> ValidationReport:
        """Run validation checks and return structured report."""

        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        files = list_markdown_files(root)
        concepts = [p for p in files if p.name not in RESERVED_FILENAMES]

        graph = nx.DiGraph()
        concept_paths = {p.relative_to(root).as_posix(): p for p in concepts}
        resources_seen: dict[str, str] = {}

        for path in concepts:
            rel = path.relative_to(root).as_posix()
            concept_id = concept_id_from_path(root, path)
            graph.add_node(concept_id)

            post = self._load_post(path, errors)
            if post is None:
                continue

            meta = post.metadata or {}
            type_value = str(meta.get("type", "")).strip()
            if not type_value:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="MISSING_REQUIRED_TYPE",
                        message="Missing required frontmatter key: type",
                        path=rel,
                    )
                )

            for rec_key in ["title", "description", "resource", "timestamp"]:
                value = meta.get(rec_key)
                if value is None or str(value).strip() == "":
                    warnings.append(
                        ValidationIssue(
                            severity="warning",
                            code="MISSING_RECOMMENDED_METADATA",
                            message=f"Missing recommended key: {rec_key}",
                            path=rel,
                        )
                    )

            title = str(meta.get("title", "")).strip().lower()
            type_lower = type_value.lower()
            dedupe_key = f"{type_lower}:{title}"
            if title and dedupe_key in resources_seen:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="DUPLICATE_CONCEPT",
                        message=f"Duplicate concept by type/title with {resources_seen[dedupe_key]}",
                        path=rel,
                    )
                )
            elif title:
                resources_seen[dedupe_key] = rel

            links = extract_markdown_links(post.content)
            for link in links:
                target_path = self._resolve_local_link(root=root, source=path, link=link)
                if target_path is None:
                    continue

                normalized = target_path.relative_to(root).as_posix() if target_path.exists() else ""
                if not target_path.exists() or normalized not in concept_paths:
                    errors.append(
                        ValidationIssue(
                            severity="error",
                            code="BROKEN_LINK",
                            message=f"Broken concept link: {link}",
                            path=rel,
                        )
                    )
                    continue

                graph.add_edge(concept_id, concept_id_from_path(root, target_path))

        for orphan in self._find_orphans(graph):
            warnings.append(
                ValidationIssue(
                    severity="warning",
                    code="ORPHAN_CONCEPT",
                    message="Concept has no incoming/outgoing concept references",
                    path=orphan,
                )
            )

        for cycle in nx.simple_cycles(graph):
            cycle_path = " -> ".join(cycle)
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="CIRCULAR_REFERENCE",
                    message=f"Circular reference detected: {cycle_path}",
                )
            )

        report = ValidationReport(
            passed=not errors,
            errors=errors,
            warnings=warnings,
            stats={
                "files_total": len(files),
                "concept_files": len(concepts),
                "error_count": len(errors),
                "warning_count": len(warnings),
            },
        )
        logger.info(
            "Validation complete. passed={} errors={} warnings={}",
            report.passed,
            len(errors),
            len(warnings),
        )
        return report

    def _load_post(self, path: Path, errors: list[ValidationIssue]):
        rel = path.as_posix()
        try:
            return frontmatter.load(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="INVALID_FRONTMATTER",
                    message=f"Failed to parse frontmatter: {exc}",
                    path=rel,
                )
            )
            return None

    def _resolve_local_link(self, root: Path, source: Path, link: str) -> Path | None:
        trimmed = link.strip()
        if not trimmed or trimmed.startswith(("http://", "https://", "mailto:", "#")):
            return None

        clean = trimmed.split("#", 1)[0]
        candidate = root / clean.lstrip("/") if clean.startswith("/") else (source.parent / clean).resolve()

        return candidate

    def _find_orphans(self, graph: nx.DiGraph) -> list[str]:
        orphans: list[str] = []
        for node in graph.nodes:
            if graph.in_degree(node) == 0 and graph.out_degree(node) == 0:
                orphans.append(node)
        return orphans

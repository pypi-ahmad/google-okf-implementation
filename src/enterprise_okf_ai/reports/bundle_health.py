"""Bundle health reporting for OKF validation and graph diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx

from graph.builder import KnowledgeGraphBuilder
from validators.okf_validator import OKFValidator as StrictOKFValidator
from validators.okf_validator import ValidationReport


@dataclass(slots=True)
class BundleHealthReport:
    """Combined validation and graph health report."""

    okf_dir: Path
    generated_at: str
    validation_passed: bool
    error_count: int
    warning_count: int
    validation_stats: dict[str, int]
    graph_stats: dict[str, int | float]
    relation_counts: dict[str, int]
    cycles: list[list[str]]
    orphan_nodes: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Serialize report as JSON-friendly dict."""

        return {
            "okf_dir": self.okf_dir.as_posix(),
            "generated_at": self.generated_at,
            "validation_passed": self.validation_passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "validation_stats": self.validation_stats,
            "graph_stats": self.graph_stats,
            "relation_counts": self.relation_counts,
            "cycles": self.cycles,
            "orphan_nodes": self.orphan_nodes,
        }

    def to_markdown(self) -> str:
        """Render compact markdown summary suitable for CI artifacts."""

        lines = [
            "# OKF Bundle Health Report",
            "",
            f"- Bundle: `{self.okf_dir.as_posix()}`",
            f"- Generated at: `{self.generated_at}`",
            f"- Validation passed: `{self.validation_passed}`",
            f"- Errors: `{self.error_count}`",
            f"- Warnings: `{self.warning_count}`",
            "",
            "## Validation Stats",
        ]

        for key, value_int in sorted(self.validation_stats.items()):
            lines.append(f"- {key}: `{value_int}`")

        lines.extend(["", "## Graph Stats"])
        for key, value_stat in sorted(self.graph_stats.items()):
            lines.append(f"- {key}: `{value_stat}`")

        lines.extend(["", "## Relation Counts"])
        if self.relation_counts:
            for key, value in sorted(self.relation_counts.items()):
                lines.append(f"- {key}: `{value}`")
        else:
            lines.append("- none")

        lines.extend(["", "## Cycles"])
        if self.cycles:
            for cycle in self.cycles:
                lines.append(f"- {' -> '.join(cycle)}")
        else:
            lines.append("- none")

        lines.extend(["", "## Orphan Nodes"])
        if self.orphan_nodes:
            for node in self.orphan_nodes:
                lines.append(f"- {node}")
        else:
            lines.append("- none")

        return "\n".join(lines).rstrip() + "\n"


class BundleHealthReporter:
    """Generate cross-cutting bundle health report from validator + graph builder."""

    def __init__(self, validator: StrictOKFValidator | None = None):
        self._validator = validator or StrictOKFValidator()

    def generate(self, okf_dir: str | Path) -> BundleHealthReport:
        """Build a single health report from validation and graph diagnostics."""

        root = Path(okf_dir)
        validation = self._validator.validate(root)

        graph_builder = KnowledgeGraphBuilder(root)
        graph = graph_builder.build() if root.exists() else nx.DiGraph()

        graph_stats = self._graph_stats(graph)
        relation_counts = self._relation_counts(graph)
        cycles = [cycle for cycle in nx.simple_cycles(graph) if len(cycle) > 1]
        orphan_nodes = sorted([node for node in graph.nodes if graph.in_degree(node) == 0 and graph.out_degree(node) == 0])

        return BundleHealthReport(
            okf_dir=root,
            generated_at=datetime.now(timezone.utc).isoformat(),
            validation_passed=validation.passed,
            error_count=len(validation.errors),
            warning_count=len(validation.warnings),
            validation_stats=validation.stats,
            graph_stats=graph_stats,
            relation_counts=relation_counts,
            cycles=cycles,
            orphan_nodes=orphan_nodes,
        )

    def write_json(self, report: BundleHealthReport, output_path: str | Path) -> Path:
        """Write report JSON to disk."""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        import json

        path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return path

    def write_markdown(self, report: BundleHealthReport, output_path: str | Path) -> Path:
        """Write report markdown summary to disk."""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report.to_markdown(), encoding="utf-8")
        return path

    def _graph_stats(self, graph: nx.DiGraph) -> dict[str, int | float]:
        nodes = graph.number_of_nodes()
        edges = graph.number_of_edges()

        weak_components = nx.number_weakly_connected_components(graph) if nodes > 0 else 0
        strong_components = nx.number_strongly_connected_components(graph) if nodes > 0 else 0
        density = nx.density(graph) if nodes > 1 else 0.0

        return {
            "nodes": nodes,
            "edges": edges,
            "weakly_connected_components": weak_components,
            "strongly_connected_components": strong_components,
            "density": round(float(density), 6),
        }

    def _relation_counts(self, graph: nx.DiGraph) -> dict[str, int]:
        counts: dict[str, int] = {}
        for _, _, attrs in graph.edges(data=True):
            relations = attrs.get("relations")
            normalized = (
                {str(item) for item in relations}
                if isinstance(relations, list)
                else {str(attrs.get("relation", "related_to"))}
            )

            for relation in normalized:
                counts[relation] = counts.get(relation, 0) + 1
        return counts


def summarize_bundle_health(okf_dir: str | Path) -> tuple[ValidationReport, BundleHealthReport]:
    """Convenience helper returning raw validation and summary report."""

    validator = StrictOKFValidator()
    validation = validator.validate(okf_dir)
    summary = BundleHealthReporter(validator=validator).generate(okf_dir)
    return validation, summary

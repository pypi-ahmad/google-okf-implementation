from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import yaml

from enterprise_okf_ai.reports import BundleHealthReporter
from graph.builder import KnowledgeGraphBuilder
from validators.okf_validator import OKFValidator

DEFAULT_TIMESTAMP = "2026-07-03T00:00:00+00:00"


def _write_okf(path: Path, frontmatter: dict[str, object], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=False).strip()
    path.write_text(f"---\n{fm}\n---\n\n{body.strip()}\n", encoding="utf-8")


def _frontmatter(
    concept_id: str,
    concept_type: str,
    title: str,
    description: str,
    resource: str,
    sources: list[str],
    relationships: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "id": concept_id,
        "type": concept_type,
        "title": title,
        "description": description,
        "tags": [concept_type],
        "resource": resource,
        "sources": sources,
        "relationships": relationships or [],
        "timestamp": DEFAULT_TIMESTAMP,
    }


def test_prompt4_validator_detects_required_rules(tmp_path: Path) -> None:
    root = tmp_path / "okf"

    _write_okf(
        root / "datasets" / "orders.md",
        _frontmatter(
            concept_id="dataset:orders",
            concept_type="dataset",
            title="Orders",
            description="Orders canonical dataset",
            resource="datasets/orders.md",
            sources=["datasets/orders.md"],
            relationships=[
                {
                    "type": "references",
                    "target_id": "api:orders-api",
                    "target_type": "api",
                    "target_title": "Orders API",
                    "path": "apis/orders-api.md",
                }
            ],
        ),
        "# Orders\nSee [Orders API](/apis/orders-api.md)",
    )

    _write_okf(
        root / "apis" / "orders-api.md",
        _frontmatter(
            concept_id="api:orders-api",
            concept_type="api",
            title="Orders API",
            description="Updates order lifecycle",
            resource="apis/orders-api.md",
            sources=["apis/orders-api.md"],
            relationships=[
                {
                    "type": "references",
                    "target_id": "metric:mau",
                    "target_type": "metric",
                    "target_title": "Monthly Active Users",
                    "path": "metrics/mau.md",
                }
            ],
        ),
        "# Orders API\nUses [Orders](../datasets/orders.md) and [Missing](/datasets/missing.md)",
    )

    _write_okf(
        root / "metrics" / "mau.md",
        _frontmatter(
            concept_id="metric:mau",
            concept_type="metric",
            title="Monthly Active Users",
            description="Distinct active users",
            resource="metrics/mau.md",
            sources=["metrics/mau.md"],
            relationships=[
                {
                    "type": "references",
                    "target_id": "api:orders-api",
                    "target_type": "api",
                    "target_title": "Orders API",
                    "path": "apis/orders-api.md",
                }
            ],
        ),
        "# MAU\nDepends on [Orders API](/apis/orders-api.md)",
    )

    # Duplicate canonical concept id.
    _write_okf(
        root / "apis" / "orders-api-copy.md",
        _frontmatter(
            concept_id="api:orders-api",
            concept_type="api",
            title="Orders API Copy",
            description="Duplicate concept id",
            resource="apis/orders-api-copy.md",
            sources=["apis/orders-api-copy.md"],
        ),
        "# Duplicate\nNo links",
    )

    # Missing required field: resource.
    missing_resource = _frontmatter(
        concept_id="table:orders",
        concept_type="table",
        title="Orders Table",
        description="Fact table",
        resource="tables/orders.md",
        sources=["tables/orders.md"],
    )
    del missing_resource["resource"]
    _write_okf(root / "tables" / "orders.md", missing_resource, "# Orders table")

    # Orphan document.
    _write_okf(
        root / "glossary" / "term.md",
        _frontmatter(
            concept_id="glossary:sla",
            concept_type="glossary",
            title="SLA",
            description="Service level agreement",
            resource="glossary/term.md",
            sources=["glossary/term.md"],
        ),
        "# SLA\nDefinition only.",
    )

    # Invalid YAML frontmatter.
    invalid = root / "playbooks" / "invalid.md"
    invalid.parent.mkdir(parents=True, exist_ok=True)
    invalid.write_text(
        "---\nid: playbook:invalid\ntype: playbook\ntitle: Invalid\ntags: [oops\n---\n\n# broken\n",
        encoding="utf-8",
    )

    report = OKFValidator().validate(root)

    codes = {issue.code for issue in report.issues}
    assert "INVALID_YAML_FRONTMATTER" in codes
    assert "MISSING_MANDATORY_FIELDS" in codes
    assert "BROKEN_INTERNAL_LINK" in codes
    assert "ORPHAN_DOCUMENT" in codes
    assert "DUPLICATE_CONCEPT_DEFINITION" in codes
    assert "CIRCULAR_REFERENCE" in codes
    assert report.passed is False
    assert report.stats["cycles"] >= 1


def test_prompt4_graph_builder_supports_traversal_and_exports(tmp_path: Path) -> None:
    root = tmp_path / "okf"

    _write_okf(
        root / "datasets" / "orders.md",
        _frontmatter(
            concept_id="dataset:orders",
            concept_type="dataset",
            title="Orders",
            description="Orders dataset",
            resource="datasets/orders.md",
            sources=["datasets/orders.md"],
        ),
        "# Orders",
    )

    _write_okf(
        root / "metrics" / "mau.md",
        {
            **_frontmatter(
                concept_id="metric:mau",
                concept_type="metric",
                title="Monthly Active Users",
                description="Distinct active users",
                resource="metrics/mau.md",
                sources=["metrics/mau.md"],
            ),
            "dependencies": ["Orders API"],
        },
        "# MAU",
    )

    _write_okf(
        root / "apis" / "orders-api.md",
        _frontmatter(
            concept_id="api:orders-api",
            concept_type="api",
            title="Orders API",
            description="API for order writes",
            resource="apis/orders-api.md",
            sources=["apis/orders-api.md"],
            relationships=[
                {
                    "type": "references",
                    "target_id": "metric:mau",
                    "target_type": "metric",
                    "target_title": "Monthly Active Users",
                    "path": "metrics/mau.md",
                }
            ],
        ),
        "# API\nUses [Orders](/datasets/orders.md)",
    )

    builder = KnowledgeGraphBuilder(root)
    graph = builder.build()

    assert graph.number_of_nodes() == 3
    assert graph.number_of_edges() >= 3

    relation_set = {(u, v, data["relation"]) for u, v, data in graph.edges(data=True)}
    assert ("api:orders-api", "dataset:orders", "markdown_link") in relation_set
    assert ("api:orders-api", "metric:mau", "frontmatter_relationship") in relation_set
    assert ("metric:mau", "api:orders-api", "dependency") in relation_set

    neighbors = builder.neighbors("api:orders-api", depth=1, relation="frontmatter_relationship")
    assert neighbors == ["metric:mau"]

    subgraph = builder.relation_subgraph("api:orders-api", depth=2, direction="both")
    assert set(subgraph.nodes()) == {"api:orders-api", "dataset:orders", "metric:mau"}

    json_path = builder.export_json(tmp_path / "graph.json")
    graphml_path = builder.export_graphml(tmp_path / "graph.graphml")

    assert json_path.exists()
    assert graphml_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert "nodes" in payload
    assert "links" in payload

    loaded = nx.read_graphml(graphml_path)
    assert len(loaded.nodes) == 3


def test_prompt4_bundle_health_reporter_summarizes_bundle_health(tmp_path: Path) -> None:
    root = tmp_path / "okf"

    _write_okf(
        root / "datasets" / "orders.md",
        _frontmatter(
            concept_id="dataset:orders",
            concept_type="dataset",
            title="Orders",
            description="Orders dataset",
            resource="datasets/orders.md",
            sources=["datasets/orders.md"],
        ),
        "# Orders\nCanonical order records.",
    )

    _write_okf(
        root / "apis" / "orders-api.md",
        _frontmatter(
            concept_id="api:orders-api",
            concept_type="api",
            title="Orders API",
            description="API",
            resource="apis/orders-api.md",
            sources=["apis/orders-api.md"],
        ),
        "# Orders API\nSee [Orders](/datasets/orders.md)",
    )

    reporter = BundleHealthReporter()
    report = reporter.generate(root)

    assert report.validation_passed is True
    assert report.error_count == 0
    assert report.graph_stats["nodes"] == 2
    assert report.graph_stats["edges"] >= 1

    json_path = reporter.write_json(report, tmp_path / "reports" / "health.json")
    md_path = reporter.write_markdown(report, tmp_path / "reports" / "health.md")

    assert json_path.exists()
    assert md_path.exists()
    assert "OKF Bundle Health Report" in md_path.read_text(encoding="utf-8")

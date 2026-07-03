from __future__ import annotations

from pathlib import Path

import frontmatter

from enterprise_okf_ai.ingestion import IngestionService
from enterprise_okf_ai.okf import OKFBundleGenerator
from enterprise_okf_ai.validators import BundleValidator
from ingest.parser import DocumentParser


def _write_enterprise_source_docs(root: Path) -> None:
    (root / "apis").mkdir(parents=True, exist_ok=True)
    (root / "datasets").mkdir(parents=True, exist_ok=True)
    (root / "metrics").mkdir(parents=True, exist_ok=True)
    (root / "playbooks").mkdir(parents=True, exist_ok=True)
    (root / "tables").mkdir(parents=True, exist_ok=True)
    (root / "glossary").mkdir(parents=True, exist_ok=True)

    (root / "apis" / "orders_api.md").write_text(
        """
# Orders API

`PATCH /v2/orders/{order_id}` updates order status and writes to Orders Fact Table.

## Dependencies
- Customer Profile Dataset
- Monthly Active Users
        """.strip(),
        encoding="utf-8",
    )

    (root / "apis" / "orders_api_duplicate.md").write_text(
        """
# Orders API

Orders API emits `order.updated` and is consumed by Monthly Active Users dashboards.
        """.strip(),
        encoding="utf-8",
    )

    (root / "datasets" / "customer_profile.md").write_text(
        """
# Customer Profile Dataset

Primary customer dimension for retention and churn analysis.

## Consumers
- Orders API
- Monthly Active Users
        """.strip(),
        encoding="utf-8",
    )

    (root / "metrics" / "mau.md").write_text(
        """
# Monthly Active Users

Monthly Active Users is calculated from distinct active customer IDs.

## Dependencies
- Customer Profile Dataset
- Orders API
        """.strip(),
        encoding="utf-8",
    )

    (root / "playbooks" / "payment_failure_playbook.md").write_text(
        """
# Payment Failure Playbook

When payment errors exceed threshold, triage Orders API and Orders Fact Table latency.
        """.strip(),
        encoding="utf-8",
    )

    (root / "tables" / "orders_fact.csv").write_text(
        """column,type,description
order_id,STRING,Order identifier
customer_id,STRING,References Customer Profile Dataset
order_status,STRING,Current status used by Orders API
        """.strip()
        + "\n",
        encoding="utf-8",
    )

    (root / "glossary" / "platform_glossary.md").write_text(
        """
# Platform Glossary

- SLA: Service level agreement for reliability.
- MAU: Monthly Active Users business metric.
        """.strip(),
        encoding="utf-8",
    )


def _bundle_snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_okf_bundle_builder_creates_strict_hierarchy_and_frontmatter(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / "bundle"
    _write_enterprise_source_docs(source_root)

    ingestion = IngestionService(DocumentParser())
    docs = ingestion.ingest(source_root)

    report = OKFBundleGenerator(output_dir=output_root, source_dir=source_root).build(docs)

    assert report.concept_count > 0
    assert report.deduplicated_concepts >= 1

    for folder in ["datasets", "apis", "metrics", "playbooks", "tables", "glossary"]:
        assert (output_root / folder).exists()

    api_file = output_root / "apis" / "orders-api.md"
    assert api_file.exists()

    api_post = frontmatter.load(api_file)
    required_keys = {
        "id",
        "type",
        "title",
        "description",
        "tags",
        "resource",
        "sources",
        "relationships",
        "timestamp",
    }

    assert required_keys.issubset(api_post.metadata.keys())
    assert len(api_post.metadata["sources"]) == 2
    assert "## Source References" in api_post.content
    assert "## Relationships" in api_post.content


def test_okf_bundle_builder_is_reproducible(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    bundle_a = tmp_path / "bundle_a"
    bundle_b = tmp_path / "bundle_b"
    _write_enterprise_source_docs(source_root)

    ingestion = IngestionService(DocumentParser())
    docs = ingestion.ingest(source_root)

    OKFBundleGenerator(output_dir=bundle_a, source_dir=source_root).build(docs)
    OKFBundleGenerator(output_dir=bundle_b, source_dir=source_root).build(docs)

    assert _bundle_snapshot(bundle_a) == _bundle_snapshot(bundle_b)


def test_okf_bundle_markdown_relationship_links_are_github_readable(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / "bundle"
    _write_enterprise_source_docs(source_root)

    ingestion = IngestionService(DocumentParser())
    docs = ingestion.ingest(source_root)
    OKFBundleGenerator(output_dir=output_root, source_dir=source_root).build(docs)

    for md_file in sorted(output_root.rglob("*.md")):
        if md_file.name == "README.md":
            continue

        post = frontmatter.load(md_file)
        assert isinstance(post.metadata, dict)
        assert post.content.strip().startswith("#")

        for relationship in post.metadata.get("relationships", []):
            link_path = relationship["path"]
            assert (output_root / link_path).exists()


def test_okf_bundle_relationship_resolution_avoids_cycles_and_orphans(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / "bundle"
    _write_enterprise_source_docs(source_root)

    ingestion = IngestionService(DocumentParser())
    docs = ingestion.ingest(source_root)
    OKFBundleGenerator(output_dir=output_root, source_dir=source_root).build(docs)

    report = BundleValidator().validate(output_root)
    assert report.passed is True
    assert len(report.errors) == 0
    assert len(report.warnings) == 0
    assert report.stats.get("cycles", 0) == 0
    assert report.stats.get("orphans", 0) == 0

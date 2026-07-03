from pathlib import Path

from okfhub.docs_generator import DocumentationGenerator


def _write_doc(path: Path, title: str, concept_type: str, description: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""
---
type: {concept_type}
title: {title}
description: {description}
tags: []
resource: internal
timestamp: 2026-07-01T00:00:00Z
---

{body}
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_docs_generator_outputs_dependency_report(tmp_path: Path) -> None:
    okf_root = tmp_path / "bundle"
    out_root = tmp_path / "generated"

    _write_doc(
        okf_root / "apis" / "orders-api.md",
        title="Orders API",
        concept_type="api",
        description="Updates orders",
        body="# Summary\nUses [Orders Table](/tables/orders.md)",
    )
    _write_doc(
        okf_root / "tables" / "orders.md",
        title="Orders Table",
        concept_type="table",
        description="Warehouse table",
        body="# Summary\nNo deps",
    )

    files = DocumentationGenerator().generate(okf_root=okf_root, output_dir=out_root)

    assert len(files) == 5
    dep_file = out_root / "dependency_report.generated.md"
    assert dep_file.exists()
    content = dep_file.read_text(encoding="utf-8")
    assert "Link Volume by Concept Type" in content
    assert "Orders API" in content

import json
from pathlib import Path

from graph.builder import KnowledgeGraphBuilder


def _write_concept(path: Path, frontmatter: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8")


def test_graph_builder_builds_and_exports(tmp_path: Path) -> None:
    root = tmp_path / "okf"

    _write_concept(
        root / "datasets" / "orders.md",
        """
type: dataset
title: Orders
description: Orders dataset
tags: [warehouse]
resource: warehouse.orders
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "# Summary\nReferenced by API",
    )

    _write_concept(
        root / "apis" / "orders-api.md",
        """
type: api
title: Orders API
description: Updates orders
tags: [api]
resource: orders.api
timestamp: 2026-07-03T00:00:00Z
dependencies: [Orders]
""".strip(),
        "# Summary\nUses [Orders](/datasets/orders.md)",
    )

    builder = KnowledgeGraphBuilder(root)
    graph = builder.build()

    assert graph.number_of_nodes() == 2
    assert graph.number_of_edges() >= 1

    json_path = builder.export_json(tmp_path / "graph.json")
    html_path = builder.export_html(tmp_path / "graph.html")

    assert json_path.exists()
    assert html_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert "nodes" in payload
    assert "links" in payload

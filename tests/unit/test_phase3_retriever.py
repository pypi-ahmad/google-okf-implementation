from pathlib import Path

from graph.builder import KnowledgeGraphBuilder
from rag.retriever import HybridSearchRouter


class _FakeVectorStore:
    def query(self, embedding, top_k=8):  # noqa: ANN001
        return {
            "ids": [["chunk-1"]],
            "distances": [[0.05]],
            "metadatas": [[{"source_path": "apis/orders-api.md"}]],
        }


def _write_doc(path: Path, frontmatter: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8")


def test_hybrid_router_graph_expands_api_results(tmp_path: Path) -> None:
    okf_root = tmp_path / "okf"

    _write_doc(
        okf_root / "apis" / "orders-api.md",
        """
type: api
title: Orders API
description: Updates orders
tags: [api]
resource: orders.api
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "Uses [Orders Dataset](/datasets/orders-dataset.md) and [MAU](/metrics/mau.md)",
    )

    _write_doc(
        okf_root / "datasets" / "orders-dataset.md",
        """
type: dataset
title: Orders Dataset
description: Canonical order data
tags: [dataset]
resource: warehouse.orders
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "Dataset schema",
    )

    _write_doc(
        okf_root / "metrics" / "mau.md",
        """
type: metric
title: Monthly Active Users
description: Distinct active users
tags: [metric]
resource: metrics.mau
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "Metric definition",
    )

    graph = KnowledgeGraphBuilder(okf_root).build()

    router = HybridSearchRouter(
        okf_dir=okf_root,
        vector_store=_FakeVectorStore(),
        embedding_fn=lambda texts: [[float(len(texts[0])), 1.0, 0.0]],
        graph=graph,
    )

    hits = router.search("Which API handles orders?", top_k=5, use_graph_expansion=True)

    hit_types = {hit.concept_type for hit in hits}
    assert "api" in hit_types
    assert "dataset" in hit_types
    assert "metric" in hit_types

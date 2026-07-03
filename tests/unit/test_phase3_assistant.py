from pathlib import Path

from agent.assistant import EnterpriseAssistant
from graph.builder import KnowledgeGraphBuilder
from rag.retriever import HybridSearchRouter


class _FakeVectorStore:
    def query(self, embedding, top_k=8):  # noqa: ANN001
        return {
            "ids": [["chunk-1"]],
            "distances": [[0.03]],
            "metadatas": [[{"source_path": "apis/orders-api.md"}]],
        }


def _write_doc(path: Path, frontmatter: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8")


def test_assistant_uses_required_tools_and_graph_cross_reference(tmp_path: Path) -> None:
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
        "Uses [Orders Dataset](/datasets/orders-dataset.md)",
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
        "Schema for orders",
    )

    graph = KnowledgeGraphBuilder(okf_root).build()
    router = HybridSearchRouter(
        okf_dir=okf_root,
        vector_store=_FakeVectorStore(),
        embedding_fn=lambda texts: [[float(len(texts[0])), 1.0, 0.0]],
        graph=graph,
    )

    assistant = EnterpriseAssistant(retriever=router, graph=graph, okf_dir=okf_root, llm=None)
    response = assistant.answer("Which team owns Orders API?")

    assert response.citations
    assert response.used_concepts
    trace = "\n".join(response.tool_trace)
    assert "search_vector_db" in trace
    assert "read_okf_file" in trace
    assert "query_knowledge_graph" in trace

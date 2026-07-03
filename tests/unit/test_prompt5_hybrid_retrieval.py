from __future__ import annotations

from pathlib import Path

from graph.builder import KnowledgeGraphBuilder
from rag.evaluation import (
    RetrievalBenchmarkSample,
    RetrievalEvaluator,
    answer_support_score,
    mean_reciprocal_rank,
    recall_at_k,
)
from rag.retriever import HybridSearchRouter


class _FakeVectorStore:
    def query(self, embedding, top_k=8):  # noqa: ANN001
        key = int(round(float(embedding[0])))
        if key == 10:
            payload = [
                ("chunk-api-orders", 0.02, {"source_path": "apis/orders-api.md"}),
                ("chunk-dataset-orders", 0.13, {"source_path": "datasets/orders-dataset.md"}),
            ]
        elif key == 20:
            payload = [
                ("chunk-table-orders", 0.01, {"source_path": "tables/orders-table.md"}),
                ("chunk-dataset-orders", 0.08, {"source_path": "datasets/orders-dataset.md"}),
            ]
        elif key == 30:
            payload = [
                ("chunk-metric-mau", 0.02, {"source_path": "metrics/mau.md"}),
                ("chunk-api-orders", 0.22, {"source_path": "apis/orders-api.md"}),
            ]
        else:
            payload = [
                ("chunk-api-orders", 0.07, {"source_path": "apis/orders-api.md"}),
                ("chunk-playbook-payment", 0.09, {"source_path": "playbooks/payment-failure.md"}),
            ]

        payload = payload[:top_k]
        return {
            "ids": [[item[0] for item in payload]],
            "distances": [[item[1] for item in payload]],
            "metadatas": [[item[2] for item in payload]],
        }


def _embed(texts: list[str]) -> list[list[float]]:
    query = texts[0].lower()
    if "depend" in query or "updates customer orders" in query:
        return [[10.0, 0.0, 0.0]]
    if "schema" in query or "column" in query or "table" in query:
        return [[20.0, 0.0, 0.0]]
    if "monthly active users" in query or "mau" in query:
        return [[30.0, 0.0, 0.0]]
    return [[40.0, 0.0, 0.0]]


def _write_doc(path: Path, frontmatter: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8")


def _build_router(tmp_path: Path) -> HybridSearchRouter:
    okf_root = tmp_path / "okf"

    _write_doc(
        okf_root / "apis" / "orders-api.md",
        """
type: api
title: Orders API
description: API that updates customer orders
tags: [api, orders]
resource: services.orders.v1
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        (
            "# Orders API\n"
            "Writes order lifecycle state. Depends on [Orders Dataset](/datasets/orders-dataset.md) "
            "and [Monthly Active Users](/metrics/mau.md)."
        ),
    )

    _write_doc(
        okf_root / "datasets" / "orders-dataset.md",
        """
type: dataset
title: Orders Dataset
description: Canonical warehouse dataset for orders
tags: [dataset, warehouse]
resource: warehouse.orders
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "# Orders Dataset\nSchema owner: Analytics Engineering.",
    )

    _write_doc(
        okf_root / "tables" / "orders-table.md",
        """
type: table
title: Orders Table
description: Physical schema for the warehouse orders table
tags: [schema, table]
resource: warehouse.orders_table
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "# Orders Table\nColumns: order_id, customer_id, order_total, created_at.",
    )

    _write_doc(
        okf_root / "metrics" / "mau.md",
        """
type: metric
title: Monthly Active Users
description: Distinct active users in a calendar month
tags: [metric, kpi]
resource: metrics.mau
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "# MAU\nFormula: COUNT(DISTINCT user_id) with 30-day calendar boundaries.",
    )

    _write_doc(
        okf_root / "playbooks" / "payment-failure.md",
        """
type: playbook
title: Payment Failure Runbook
description: Escalation procedure for payment processing outages
tags: [runbook, incidents]
resource: playbooks/payment-failure
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "# Payment Failure\nRun this runbook if payment retries exceed threshold.",
    )

    graph = KnowledgeGraphBuilder(okf_root).build()
    return HybridSearchRouter(
        okf_dir=okf_root,
        vector_store=_FakeVectorStore(),
        embedding_fn=_embed,
        graph=graph,
    )


def test_prompt5_auto_router_chooses_graph_for_relationship_queries(tmp_path: Path) -> None:
    router = _build_router(tmp_path)

    response = router.search_with_trace(
        query="Which dataset does Orders API depend on?",
        top_k=5,
        use_graph_expansion=True,
        route="auto",
    )

    assert response.route == "graph"
    assert response.results
    assert any("graph traversal" in item for item in response.router_trace)
    for hit in response.results:
        assert "final" in hit.score_breakdown
        assert hit.explanation_trace


def test_prompt5_keyword_route_prioritizes_structured_schema_docs(tmp_path: Path) -> None:
    router = _build_router(tmp_path)

    response = router.search_with_trace(
        query="Show schema columns for warehouse orders table",
        top_k=4,
        use_graph_expansion=False,
        route="auto",
    )

    assert response.route == "keyword"
    assert response.results[0].concept_type in {"table", "dataset"}
    assert any(hit.concept_id == "tables/orders-table" for hit in response.results[:2])
    assert all("route=" in " ".join(hit.explanation_trace) for hit in response.results)


def test_prompt5_ranked_results_include_scores_and_traces(tmp_path: Path) -> None:
    router = _build_router(tmp_path)

    hits = router.search(
        query="Which API updates customer orders?",
        top_k=5,
        use_graph_expansion=True,
        route="hybrid",
    )

    assert hits
    assert hits == sorted(hits, key=lambda item: item.score, reverse=True)
    hit_types = {hit.concept_type for hit in hits}
    assert "api" in hit_types
    assert "dataset" in hit_types
    assert "metric" in hit_types
    assert all("final" in hit.score_breakdown for hit in hits)
    assert all(hit.explanation_trace for hit in hits)


def test_prompt5_retrieval_evaluation_metrics(tmp_path: Path) -> None:
    router = _build_router(tmp_path)
    evaluator = RetrievalEvaluator(router)

    report = evaluator.evaluate(
        samples=[
            RetrievalBenchmarkSample(
                query="Which API updates customer orders?",
                expected_concept_ids=["apis/orders-api", "datasets/orders-dataset"],
                support_terms=["updates customer orders", "warehouse orders"],
                route="hybrid",
            ),
            RetrievalBenchmarkSample(
                query="How is Monthly Active Users calculated?",
                expected_concept_ids=["metrics/mau"],
                support_terms=["distinct active users", "calendar month"],
                route="auto",
            ),
        ],
        top_k=5,
        use_graph_expansion=True,
    )

    assert report.summary.total_queries == 2
    assert 0.0 <= report.summary.avg_recall_at_k <= 1.0
    assert 0.0 <= report.summary.avg_mrr <= 1.0
    assert 0.0 <= report.summary.avg_answer_support <= 1.0
    assert report.summary.avg_recall_at_k >= 0.5
    assert report.summary.avg_mrr >= 0.4

    # Direct metric utility checks.
    assert recall_at_k(["a", "b"], ["x", "a", "b"], k=2) == 0.5
    assert mean_reciprocal_rank(["target"], ["other", "target"]) == 0.5

    support = answer_support_score(
        expected=["apis/orders-api"],
        retrieved_results=router.search("Which API updates customer orders?", top_k=3),
        support_terms=["customer orders"],
    )
    assert 0.0 <= support <= 1.0

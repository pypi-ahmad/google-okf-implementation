from __future__ import annotations

from pathlib import Path

from agent.assistant import EnterpriseAssistant
from enterprise_okf_ai.agent import AgentBenchmarkCase, AgentEvaluationHarness, AgentOrchestrator
from graph.builder import KnowledgeGraphBuilder
from rag.retriever import HybridSearchRouter


class _FakeVectorStore:
    def query(self, embedding, top_k=8):  # noqa: ANN001
        key = int(round(float(embedding[0])))
        if key == 10:
            payload = [
                ("chunk-api-orders", 0.03, {"source_path": "apis/orders-api.md"}),
                ("chunk-dataset-orders", 0.06, {"source_path": "datasets/orders-dataset.md"}),
            ]
        elif key == 20:
            payload = []
        else:
            payload = [
                ("chunk-metric-mau", 0.04, {"source_path": "metrics/mau.md"}),
            ]

        payload = payload[:top_k]
        return {
            "ids": [[item[0] for item in payload]],
            "distances": [[item[1] for item in payload]],
            "metadatas": [[item[2] for item in payload]],
        }


def _embed(texts: list[str]) -> list[list[float]]:
    query = texts[0].lower()
    if "depend" in query or "owner" in query or "owns" in query:
        return [[10.0, 0.0, 0.0]]
    if "retention" in query or "payroll" in query:
        return [[20.0, 0.0, 0.0]]
    return [[30.0, 0.0, 0.0]]


def _write_doc(path: Path, frontmatter: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8")


def _build_assistant(tmp_path: Path) -> EnterpriseAssistant:
    okf_root = tmp_path / "okf"

    _write_doc(
        okf_root / "apis" / "orders-api.md",
        """
type: api
title: Orders API
description: Updates order status
tags: [api]
resource: orders.api
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "Owner: Order Platform Team. Depends on [Orders Dataset](/datasets/orders-dataset.md).",
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
        "Dataset consumed by Orders API.",
    )
    _write_doc(
        okf_root / "metrics" / "mau.md",
        """
type: metric
title: Monthly Active Users
description: Distinct customer count
tags: [metric]
resource: metrics.mau
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "Formula: COUNT(DISTINCT customer_id).",
    )

    graph = KnowledgeGraphBuilder(okf_root).build()
    router = HybridSearchRouter(
        okf_dir=okf_root,
        vector_store=_FakeVectorStore(),
        embedding_fn=_embed,
        graph=graph,
    )
    return EnterpriseAssistant(retriever=router, graph=graph, okf_dir=okf_root, llm=None)


def test_prompt6_agent_prefers_graph_for_structured_question(tmp_path: Path) -> None:
    assistant = _build_assistant(tmp_path)
    response = assistant.answer("Which dataset does Orders API depend on?")

    assert response.strategy == "graph_first"
    assert response.supported is True
    assert response.citations
    assert any(call.tool_name == "query_knowledge_graph" for call in response.tool_calls)
    assert "apis/orders-api" in response.used_concepts
    assert "search_okf_documents" in "\n".join(response.tool_trace)
    assert "search_vector_db" in "\n".join(response.tool_trace)
    assert "read_okf_file" in "\n".join(response.tool_trace)


def test_prompt6_agent_abstains_on_unsupported_question(tmp_path: Path) -> None:
    assistant = _build_assistant(tmp_path)
    response = assistant.answer("What is the legal payroll data retention schedule?", top_k=5)

    assert response.supported is False
    assert response.unsupported_reason is not None
    assert "grounded evidence" in response.answer.lower()


def test_prompt6_agent_evaluation_harness(tmp_path: Path) -> None:
    assistant = _build_assistant(tmp_path)
    orchestrator = AgentOrchestrator(assistant)
    harness = AgentEvaluationHarness(orchestrator)

    report = harness.run(
        cases=[
            AgentBenchmarkCase(
                case_id="c1",
                question="Which dataset does Orders API depend on?",
                expected_concepts=["apis/orders-api", "datasets/orders-dataset"],
                support_terms=["Orders Dataset"],
                should_abstain=False,
            ),
            AgentBenchmarkCase(
                case_id="c2",
                question="What is the legal payroll data retention schedule?",
                expected_concepts=[],
                support_terms=[],
                should_abstain=True,
            ),
        ],
        top_k=6,
    )

    assert report.summary.total_cases == 2
    assert 0.0 <= report.summary.avg_concept_recall <= 1.0
    assert 0.0 <= report.summary.avg_answer_support <= 1.0
    assert 0.0 <= report.summary.abstain_accuracy <= 1.0

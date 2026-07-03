from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from enterprise_okf_ai.agent import AgentEvaluationHarness, AgentOrchestrator
from enterprise_okf_ai.api.app import create_app
from enterprise_okf_ai.core.embeddings import deterministic_embedding
from enterprise_okf_ai.core.settings import Settings
from enterprise_okf_ai.graph import GraphService
from enterprise_okf_ai.ingestion import IngestionService
from enterprise_okf_ai.okf import OKFBundleGenerator
from enterprise_okf_ai.retrieval import RetrievalService
from enterprise_okf_ai.retrieval.evaluation import RetrievalBenchmarkSample, RetrievalEvaluator
from enterprise_okf_ai.validators import BundleValidator
from ingest.parser import DocumentParser
from vector_db.indexer import OKFVectorIndexer


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _samples() -> list[RetrievalBenchmarkSample]:
    return [
        RetrievalBenchmarkSample(
            query="Which API updates customer orders?",
            expected_concept_ids=["apis/orders-api", "datasets/customer-profile-dataset"],
            support_terms=["PATCH /v2/orders/{order_id}", "Customer Profile Dataset"],
            route="hybrid",
        ),
        RetrievalBenchmarkSample(
            query="How is Monthly Active Users calculated?",
            expected_concept_ids=["metrics/monthly-active-users"],
            support_terms=["COUNT(DISTINCT customer_id)", "analytics month"],
            route="auto",
        ),
        RetrievalBenchmarkSample(
            query="Show me the runbook for payment failures.",
            expected_concept_ids=["playbooks/payment-failure-playbook"],
            support_terms=["error rate above 3%", "triage steps"],
            route="auto",
        ),
    ]


@pytest.mark.asyncio
async def test_real_end_to_end_examples_dataset_no_smoke(tmp_path: Path) -> None:
    root = _repo_root()
    raw_dir = root / "examples" / "enterprise_docs"
    benchmark_path = root / "examples" / "eval" / "agent_benchmark.json"

    okf_dir = tmp_path / "okf_bundle"
    vector_dir = tmp_path / "vector_db"
    graph_dir = tmp_path / "graph"

    parsed_docs = IngestionService(parser=DocumentParser()).ingest(raw_dir, recursive=True, fail_fast=True)
    assert len(parsed_docs) == 8
    assert all(not document.errors for document in parsed_docs)

    build_report = OKFBundleGenerator(output_dir=okf_dir, source_dir=raw_dir).build(parsed_docs)
    assert build_report.concept_count == 9

    validation = BundleValidator().validate(okf_dir)
    assert validation.passed is True
    assert len(validation.errors) == 0
    assert len(validation.warnings) == 0
    assert validation.stats.get("cycles", 0) == 0
    assert validation.stats.get("orphans", 0) == 0

    graph = GraphService(okf_dir).build_and_export(
        json_path=graph_dir / "graph.json",
        html_path=graph_dir / "graph.html",
        graphml_path=graph_dir / "graph.graphml",
    )
    assert graph.nodes == 9
    assert graph.edges >= 8

    index_stats = OKFVectorIndexer(
        okf_dir=okf_dir,
        persist_dir=vector_dir,
        embedding_fn=deterministic_embedding,
    ).index()
    assert index_stats["files_scanned"] == 9
    assert index_stats["files_changed"] == 9
    assert index_stats["chunks_indexed"] >= 9

    retrieval = RetrievalService.from_okf(
        okf_dir=okf_dir,
        vector_dir=vector_dir,
        embedding_fn=deterministic_embedding,
        include_graph=True,
    )
    search_response = retrieval.search_with_trace(
        query="Which API updates order status?",
        top_k=6,
        route="auto",
    )
    assert search_response.results
    assert search_response.router_trace
    assert search_response.results[0].score > 0.0

    retrieval_eval = RetrievalEvaluator(retrieval.router).evaluate(
        samples=_samples(),
        top_k=6,
        use_graph_expansion=True,
    )
    assert retrieval_eval.summary.total_queries == 3
    assert retrieval_eval.summary.avg_recall_at_k >= 0.5
    assert retrieval_eval.summary.avg_mrr > 0.0
    assert retrieval_eval.summary.avg_answer_support > 0.0

    orchestrator = AgentOrchestrator.from_okf(
        okf_dir=okf_dir,
        vector_dir=vector_dir,
        embedding_fn=deterministic_embedding,
        llm=None,
    )
    agent_response = orchestrator.ask(
        question="Which API updates order status and what dataset does it depend on?",
        top_k=8,
    )
    assert agent_response.supported is True
    assert agent_response.citations
    assert agent_response.used_concepts

    harness = AgentEvaluationHarness(orchestrator)
    cases = harness.load_cases(benchmark_path)
    agent_eval = harness.run(cases=cases, top_k=8)
    assert agent_eval.summary.total_cases == 4
    assert 0.0 <= agent_eval.summary.supported_rate <= 1.0
    assert 0.0 <= agent_eval.summary.abstain_accuracy <= 1.0

    app = create_app(
        settings=Settings(
            okf_dir=okf_dir,
            vector_dir=vector_dir,
            graph_dir=graph_dir,
        )
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        health = await client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        retrieval_api = await client.post(
            "/retrieval/search",
            json={"query": "Which API updates order status?", "top_k": 6, "route": "auto", "with_trace": True},
        )
        assert retrieval_api.status_code == 200
        assert retrieval_api.json()["results"]

        ask_api = await client.post(
            "/agent/ask",
            json={"question": "Show me the runbook for payment failures.", "top_k": 8},
        )
        assert ask_api.status_code == 200
        assert "answer" in ask_api.json()

        eval_api = await client.post(
            "/agent/evaluate",
            json={"benchmark_path": benchmark_path.as_posix(), "top_k": 8},
        )
        assert eval_api.status_code == 200
        assert eval_api.json()["summary"]["total_cases"] == 4

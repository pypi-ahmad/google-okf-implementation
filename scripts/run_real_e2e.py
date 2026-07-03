"""Execute a full non-smoke end-to-end run on a realistic OKF corpus.

This script performs:
1) ingestion and normalization,
2) OKF bundle generation,
3) strict validation,
4) graph build and export,
5) vector indexing,
6) retrieval + retrieval evaluation,
7) agent answer + agent evaluation,
8) FastAPI runtime checks (health, retrieval, ask, evaluate).
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import httpx

from enterprise_okf_ai.agent import AgentEvaluationHarness, AgentOrchestrator
from enterprise_okf_ai.api import create_app
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run full non-smoke enterprise OKF AI pipeline.")
    parser.add_argument("--input-dir", type=Path, default=Path("examples/enterprise_docs"))
    parser.add_argument("--benchmark-path", type=Path, default=Path("examples/eval/agent_benchmark.json"))
    parser.add_argument("--artifacts-dir", type=Path, default=Path("artifacts/e2e_real_run"))
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--strict", action="store_true", help="Fail if validation errors OR warnings are non-zero.")
    return parser


async def _run_api_checks(settings: Settings, benchmark_path: Path, top_k: int) -> dict[str, int]:
    app = create_app(settings=settings)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        health = await client.get("/health")
        retrieval = await client.post(
            "/retrieval/search",
            json={"query": "Which API updates customer orders?", "top_k": top_k, "route": "auto", "with_trace": True},
        )
        ask = await client.post(
            "/agent/ask",
            json={"question": "Show me the runbook for payment failures.", "top_k": top_k},
        )
        evaluate = await client.post(
            "/agent/evaluate",
            json={"benchmark_path": benchmark_path.as_posix(), "top_k": top_k},
        )

    return {
        "health": health.status_code,
        "retrieval": retrieval.status_code,
        "ask": ask.status_code,
        "evaluate": evaluate.status_code,
    }


def _retrieval_eval_samples() -> list[RetrievalBenchmarkSample]:
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


def run_pipeline(
    input_dir: Path,
    benchmark_path: Path,
    artifacts_dir: Path,
    top_k: int,
    strict: bool,
) -> dict[str, Any]:
    input_dir = input_dir.resolve()
    benchmark_path = benchmark_path.resolve()
    artifacts_dir = artifacts_dir.resolve()
    okf_dir = artifacts_dir / "okf_bundle"
    graph_dir = artifacts_dir / "graph"
    vector_dir = artifacts_dir / "vector_db"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    parser = DocumentParser(chunk_size_chars=1200, chunk_overlap_chars=150, recover_errors=False)
    ingestion = IngestionService(parser=parser)
    parsed_docs = ingestion.ingest(input_dir, recursive=True, fail_fast=True)

    build_report = OKFBundleGenerator(output_dir=okf_dir, source_dir=input_dir).build(parsed_docs)
    validation_report = BundleValidator().validate(okf_dir)

    validation_errors = len(validation_report.errors)
    validation_warnings = len(validation_report.warnings)
    if strict and (validation_errors > 0 or validation_warnings > 0):
        raise RuntimeError(
            f"Strict validation failed for {okf_dir}: "
            f"errors={validation_errors}, warnings={validation_warnings}"
        )

    graph_artifacts = GraphService(okf_dir).build_and_export(
        json_path=graph_dir / "graph.json",
        html_path=graph_dir / "graph.html",
        graphml_path=graph_dir / "graph.graphml",
    )

    index_stats = OKFVectorIndexer(
        okf_dir=okf_dir,
        persist_dir=vector_dir,
        embedding_fn=deterministic_embedding,
    ).index()

    retrieval = RetrievalService.from_okf(
        okf_dir=okf_dir,
        vector_dir=vector_dir,
        embedding_fn=deterministic_embedding,
        include_graph=True,
    )
    retrieval_response = retrieval.search_with_trace(
        query="Which API updates customer orders?",
        top_k=top_k,
        route="auto",
    )
    retrieval_eval = RetrievalEvaluator(retrieval.router).evaluate(
        samples=_retrieval_eval_samples(),
        top_k=top_k,
        use_graph_expansion=True,
    )

    agent = AgentOrchestrator.from_okf(
        okf_dir=okf_dir,
        vector_dir=vector_dir,
        embedding_fn=deterministic_embedding,
        llm=None,
    )
    agent_response = agent.ask(
        question="Which API updates order status and what dataset does it depend on?",
        top_k=top_k,
    )
    harness = AgentEvaluationHarness(agent)
    agent_eval = harness.run(cases=harness.load_cases(benchmark_path), top_k=top_k)

    settings = Settings(okf_dir=okf_dir, vector_dir=vector_dir, graph_dir=graph_dir)
    api_status = asyncio.run(_run_api_checks(settings=settings, benchmark_path=benchmark_path, top_k=top_k))

    summary: dict[str, Any] = {
        "input_dir": input_dir.as_posix(),
        "benchmark_path": benchmark_path.as_posix(),
        "artifacts_dir": artifacts_dir.as_posix(),
        "build": build_report.to_dict(),
        "validation": validation_report.to_dict(),
        "graph": {
            "nodes": graph_artifacts.nodes,
            "edges": graph_artifacts.edges,
            "json_path": graph_artifacts.json_path.as_posix(),
            "html_path": graph_artifacts.html_path.as_posix(),
            "graphml_path": graph_artifacts.graphml_path.as_posix() if graph_artifacts.graphml_path else None,
        },
        "indexing": index_stats,
        "retrieval": {
            "route": retrieval_response.route,
            "result_count": len(retrieval_response.results),
            "router_trace": retrieval_response.router_trace,
            "results": [
                {
                    "concept_id": result.concept_id,
                    "path": result.path,
                    "title": result.title,
                    "type": result.concept_type,
                    "score": result.score,
                    "source": result.source,
                }
                for result in retrieval_response.results
            ],
        },
        "retrieval_evaluation": {
            "summary": asdict(retrieval_eval.summary),
            "items": [asdict(item) for item in retrieval_eval.items],
        },
        "agent": {
            "supported": agent_response.supported,
            "confidence": agent_response.confidence,
            "used_concepts": agent_response.used_concepts,
            "citations": agent_response.citations,
            "strategy": agent_response.strategy,
        },
        "agent_evaluation": agent_eval.to_dict(),
        "api_status": api_status,
    }

    summary_path = artifacts_dir / "e2e_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def main() -> None:
    args = _build_parser().parse_args()
    summary = run_pipeline(
        input_dir=args.input_dir,
        benchmark_path=args.benchmark_path,
        artifacts_dir=args.artifacts_dir,
        top_k=args.top_k,
        strict=bool(args.strict),
    )

    validation = summary["validation"]
    stats = validation.get("stats", {})
    compact = {
        "summary_path": str(Path(summary["artifacts_dir"]) / "e2e_summary.json"),
        "validation_errors": len([item for item in validation.get("issues", []) if item.get("severity") == "error"]),
        "validation_warnings": len([item for item in validation.get("issues", []) if item.get("severity") == "warning"]),
        "cycles": stats.get("cycles"),
        "orphans": stats.get("orphans"),
        "graph_nodes": summary["graph"]["nodes"],
        "graph_edges": summary["graph"]["edges"],
        "retrieval_results": summary["retrieval"]["result_count"],
        "agent_supported": summary["agent"]["supported"],
        "api_status": summary["api_status"],
    }
    print(json.dumps(compact, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

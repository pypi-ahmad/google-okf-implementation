"""FastAPI application for enterprise OKF AI scaffold runtime."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from enterprise_okf_ai.agent import AgentEvaluationHarness, AgentOrchestrator
from enterprise_okf_ai.core.embeddings import deterministic_embedding
from enterprise_okf_ai.core.settings import Settings
from enterprise_okf_ai.graph import GraphService
from enterprise_okf_ai.ingestion import IngestionService
from enterprise_okf_ai.reports import BundleHealthReporter
from enterprise_okf_ai.retrieval import RetrievalService
from enterprise_okf_ai.validators import BundleValidator


class ParseRequest(BaseModel):
    """Request payload for file parsing endpoint."""

    file_path: str


class ValidateRequest(BaseModel):
    """Request payload for OKF validation endpoint."""

    okf_dir: str | None = None


class GraphBuildRequest(BaseModel):
    """Request payload for graph build endpoint."""

    okf_dir: str | None = None


class BundleReportRequest(BaseModel):
    """Request payload for bundle health report endpoint."""

    okf_dir: str | None = None


class SearchRequest(BaseModel):
    """Request payload for retrieval search endpoint."""

    query: str = Field(min_length=2)
    top_k: int = Field(default=8, ge=1, le=50)
    route: Literal["auto", "vector", "keyword", "graph", "hybrid"] = Field(default="auto")
    with_trace: bool = Field(default=False)


class AskRequest(BaseModel):
    """Request payload for agent ask endpoint."""

    question: str = Field(min_length=2)
    top_k: int = Field(default=8, ge=1, le=50)


class AgentEvalRequest(BaseModel):
    """Request payload for agent benchmark evaluation."""

    benchmark_path: str | None = None
    top_k: int = Field(default=8, ge=1, le=50)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create FastAPI app instance with scaffold-ready runtime wiring."""

    cfg = settings or Settings()
    app = FastAPI(title="enterprise-okf-ai", version="0.3.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "enterprise-okf-ai"}

    @app.post("/ingestion/parse")
    async def parse_document(payload: ParseRequest) -> dict[str, object]:
        parser = IngestionService()
        parsed = parser.parse_file(payload.file_path)
        return {
            "file_path": parsed.file_path.as_posix(),
            "file_type": parsed.file_type,
            "metadata": parsed.metadata,
            "content_preview": parsed.content[:500],
        }

    @app.post("/okf/validate")
    async def validate_bundle(payload: ValidateRequest) -> dict[str, object]:
        validator = BundleValidator()
        target_dir = Path(payload.okf_dir) if payload.okf_dir else cfg.resolve(cfg.okf_dir)
        report = validator.validate(target_dir)
        return report.to_dict()

    @app.post("/graph/build")
    async def build_graph(payload: GraphBuildRequest) -> dict[str, object]:
        target_dir = Path(payload.okf_dir) if payload.okf_dir else cfg.resolve(cfg.okf_dir)
        service = GraphService(target_dir)
        artifacts = service.build_and_export(
            json_path=cfg.resolve(cfg.graph_dir / "graph.json"),
            html_path=cfg.resolve(cfg.graph_dir / "graph.html"),
            graphml_path=cfg.resolve(cfg.graph_dir / "graph.graphml"),
        )
        return {
            "nodes": artifacts.nodes,
            "edges": artifacts.edges,
            "json_path": artifacts.json_path.as_posix(),
            "html_path": artifacts.html_path.as_posix(),
            "graphml_path": artifacts.graphml_path.as_posix() if artifacts.graphml_path else None,
        }

    @app.post("/bundle/report")
    async def bundle_report(payload: BundleReportRequest) -> dict[str, object]:
        target_dir = Path(payload.okf_dir) if payload.okf_dir else cfg.resolve(cfg.okf_dir)
        report = BundleHealthReporter().generate(target_dir)
        return report.to_dict()

    @app.post("/retrieval/search")
    async def search(payload: SearchRequest) -> dict[str, object] | list[dict[str, object]]:
        allowed_routes = {"auto", "vector", "keyword", "graph", "hybrid"}
        if payload.route not in allowed_routes:
            raise HTTPException(
                status_code=422,
                detail=f"route must be one of: {', '.join(sorted(allowed_routes))}",
            )

        try:
            service = RetrievalService.from_okf(
                okf_dir=cfg.resolve(cfg.okf_dir),
                vector_dir=cfg.resolve(cfg.vector_dir),
                embedding_fn=deterministic_embedding,
                include_graph=True,
            )
            if payload.with_trace:
                response = service.search_with_trace(
                    query=payload.query,
                    top_k=payload.top_k,
                    route=payload.route,
                )
                return {
                    "query": response.query,
                    "route": response.route,
                    "router_trace": response.router_trace,
                    "results": [
                        {
                            "concept_id": hit.concept_id,
                            "path": hit.path,
                            "title": hit.title,
                            "type": hit.concept_type,
                            "score": hit.score,
                            "source": hit.source,
                            "snippet": hit.snippet,
                            "score_breakdown": hit.score_breakdown,
                            "explanation_trace": hit.explanation_trace,
                        }
                        for hit in response.results
                    ],
                }

            hits = service.search(
                query=payload.query,
                top_k=payload.top_k,
                route=payload.route,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return [
            {
                "concept_id": hit.concept_id,
                "path": hit.path,
                "title": hit.title,
                "type": hit.concept_type,
                "score": hit.score,
                "source": hit.source,
                "snippet": hit.snippet,
                "score_breakdown": hit.score_breakdown,
                "explanation_trace": hit.explanation_trace,
            }
            for hit in hits
        ]

    @app.post("/agent/ask")
    async def ask(payload: AskRequest) -> dict[str, object]:
        try:
            orchestrator = AgentOrchestrator.from_okf(
                okf_dir=cfg.resolve(cfg.okf_dir),
                vector_dir=cfg.resolve(cfg.vector_dir),
                embedding_fn=deterministic_embedding,
                llm=None,
            )
            response = orchestrator.ask(question=payload.question, top_k=payload.top_k)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return {
            "answer": response.answer,
            "citations": response.citations,
            "used_concepts": response.used_concepts,
            "tool_trace": response.tool_trace,
            "tool_calls": [asdict(call) for call in response.tool_calls],
            "evidence_summary": response.evidence_summary,
            "confidence": response.confidence,
            "supported": response.supported,
            "unsupported_reason": response.unsupported_reason,
            "strategy": response.strategy,
        }

    @app.post("/agent/evaluate")
    async def agent_evaluate(payload: AgentEvalRequest) -> dict[str, object]:
        benchmark_path = (
            Path(payload.benchmark_path)
            if payload.benchmark_path
            else cfg.resolve(Path("examples/eval/agent_benchmark.json"))
        )

        try:
            orchestrator = AgentOrchestrator.from_okf(
                okf_dir=cfg.resolve(cfg.okf_dir),
                vector_dir=cfg.resolve(cfg.vector_dir),
                embedding_fn=deterministic_embedding,
                llm=None,
            )
            harness = AgentEvaluationHarness(orchestrator)
            cases = harness.load_cases(benchmark_path)
            report = harness.run(cases=cases, top_k=payload.top_k)
            return report.to_dict()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app()

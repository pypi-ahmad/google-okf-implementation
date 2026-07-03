"""CLI entrypoint for the canonical enterprise_okf_ai package."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Literal

import typer
import uvicorn

from enterprise_okf_ai.agent import AgentEvaluationHarness, AgentOrchestrator
from enterprise_okf_ai.api import create_app
from enterprise_okf_ai.core.embeddings import deterministic_embedding
from enterprise_okf_ai.core.settings import Settings
from enterprise_okf_ai.graph import GraphService
from enterprise_okf_ai.ingestion import IngestionService
from enterprise_okf_ai.okf import OKFBundleGenerator
from enterprise_okf_ai.reports import BundleHealthReporter
from enterprise_okf_ai.retrieval import RetrievalService
from enterprise_okf_ai.validators import BundleValidator
from ingest.parser import DocumentParser
from vector_db.indexer import OKFVectorIndexer

app = typer.Typer(help="Enterprise OKF AI command-line interface")


@app.command("ingest")
def ingest(
    path: Path = typer.Argument(..., exists=True),
    recursive: bool = typer.Option(True, help="Recurse into sub-directories when path is a directory."),
    chunk_size_chars: int = typer.Option(1200, min=200, help="Max chunk size (characters)."),
    chunk_overlap_chars: int = typer.Option(150, min=0, help="Chunk overlap (characters)."),
    fail_fast: bool = typer.Option(False, help="Stop ingestion on first parser failure."),
) -> None:
    """Ingest a file or directory and emit normalized structured JSON."""

    if chunk_overlap_chars >= chunk_size_chars:
        raise typer.BadParameter("chunk_overlap_chars must be smaller than chunk_size_chars.")

    parser = DocumentParser(
        chunk_size_chars=chunk_size_chars,
        chunk_overlap_chars=chunk_overlap_chars,
        recover_errors=not fail_fast,
    )
    service = IngestionService(parser=parser)
    documents = service.ingest(path=path, recursive=recursive, fail_fast=fail_fast)
    payload = service.to_payload(documents)
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("ingest-parse")
def ingest_parse(file_path: Path = typer.Argument(..., exists=True)) -> None:
    """Parse a source document and print a normalized summary."""

    parsed = IngestionService().parse_file(file_path)
    typer.echo(
        {
            "file_path": parsed.file_path.as_posix(),
            "file_type": parsed.file_type,
            "metadata": parsed.metadata,
            "content_preview": parsed.content[:400],
        }
    )


@app.command("build-okf")
def build_okf(
    input_dir: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
    output_dir: Path = typer.Argument(...),
    recursive: bool = typer.Option(True, help="Recurse into nested source directories."),
    chunk_size_chars: int = typer.Option(1200, min=200, help="Max chunk size used during normalization."),
    chunk_overlap_chars: int = typer.Option(150, min=0, help="Chunk overlap in characters."),
    fail_fast: bool = typer.Option(False, help="Stop on first ingestion failure."),
) -> None:
    """Build strict OKF markdown bundle from normalized enterprise documents."""

    if chunk_overlap_chars >= chunk_size_chars:
        raise typer.BadParameter("chunk_overlap_chars must be smaller than chunk_size_chars.")

    parser = DocumentParser(
        chunk_size_chars=chunk_size_chars,
        chunk_overlap_chars=chunk_overlap_chars,
        recover_errors=not fail_fast,
    )
    ingestion = IngestionService(parser=parser)
    documents = ingestion.ingest(path=input_dir, recursive=recursive, fail_fast=fail_fast)

    generator = OKFBundleGenerator(output_dir=output_dir, source_dir=input_dir)
    report = generator.build(documents)
    typer.echo(json.dumps(report.to_dict(), indent=2, sort_keys=True))


@app.command("okf-validate")
def okf_validate(okf_dir: Path = typer.Option(Path("okf_bundle"), exists=True)) -> None:
    """Validate an OKF bundle and emit diagnostics."""

    report = BundleValidator().validate(okf_dir)
    typer.echo(json.dumps(report.to_dict(), indent=2, sort_keys=True))


@app.command("bundle-report")
def bundle_report(
    okf_dir: Path = typer.Argument(..., exists=True, dir_okay=True, file_okay=False),
    output_json: Path | None = typer.Option(None, help="Optional path to write JSON report."),
    output_markdown: Path | None = typer.Option(None, help="Optional path to write Markdown report."),
) -> None:
    """Generate bundle health summary (validation + graph statistics)."""

    reporter = BundleHealthReporter()
    report = reporter.generate(okf_dir)

    if output_json is not None:
        reporter.write_json(report, output_json)
    if output_markdown is not None:
        reporter.write_markdown(report, output_markdown)

    typer.echo(json.dumps(report.to_dict(), indent=2, sort_keys=True))


@app.command("graph-build")
def graph_build(okf_dir: Path = typer.Option(Path("okf_bundle"), exists=True)) -> None:
    """Build graph artifacts from an OKF bundle."""

    cfg = Settings()
    artifacts = GraphService(okf_dir).build_and_export(
        json_path=cfg.resolve(cfg.graph_dir / "graph.json"),
        html_path=cfg.resolve(cfg.graph_dir / "graph.html"),
        graphml_path=cfg.resolve(cfg.graph_dir / "graph.graphml"),
    )
    typer.echo(
        {
            "nodes": artifacts.nodes,
            "edges": artifacts.edges,
            "json_path": artifacts.json_path.as_posix(),
            "html_path": artifacts.html_path.as_posix(),
            "graphml_path": artifacts.graphml_path.as_posix() if artifacts.graphml_path is not None else None,
        }
    )


@app.command("index-build")
def index_build(
    okf_dir: Path = typer.Option(Path("okf_bundle"), exists=True, help="OKF bundle to index."),
    vector_dir: Path | None = typer.Option(None, help="Chroma persist directory (defaults to Settings().vector_dir)."),
) -> None:
    """Build or refresh the local vector index for an OKF bundle.

    This must be run (and re-run after any bundle change) before
    `retrieve-search` or `agent-ask`, which read from the persisted
    index rather than the bundle directly.
    """

    cfg = Settings()
    target_vector_dir = vector_dir if vector_dir is not None else cfg.resolve(cfg.vector_dir)
    indexer = OKFVectorIndexer(
        okf_dir=okf_dir,
        persist_dir=target_vector_dir,
        embedding_fn=deterministic_embedding,
    )
    stats = indexer.index()
    typer.echo(json.dumps({"vector_dir": str(target_vector_dir), **stats}, indent=2, sort_keys=True))


@app.command("retrieve-search")
def retrieve_search(
    query: str = typer.Argument(...),
    top_k: int = typer.Option(8, min=1, max=50),
    route: Literal["auto", "vector", "keyword", "graph", "hybrid"] = typer.Option(
        "auto",
        help="Retrieval route: auto | vector | keyword | graph | hybrid.",
    ),
    with_trace: bool = typer.Option(False, help="Include router explanation trace in output."),
) -> None:
    """Run hybrid retrieval against persisted OKF/vector artifacts."""

    cfg = Settings()
    service = RetrievalService.from_okf(
        okf_dir=cfg.resolve(cfg.okf_dir),
        vector_dir=cfg.resolve(cfg.vector_dir),
        embedding_fn=deterministic_embedding,
        include_graph=True,
    )

    if with_trace:
        response = service.search_with_trace(query=query, top_k=top_k, route=route)
        payload: dict[str, object] = {
            "query": response.query,
            "route": response.route,
            "router_trace": response.router_trace,
            "results": [
                {
                    "concept_id": hit.concept_id,
                    "title": hit.title,
                    "type": hit.concept_type,
                    "score": round(hit.score, 4),
                    "source": hit.source,
                    "path": hit.path,
                    "score_breakdown": hit.score_breakdown,
                    "explanation_trace": hit.explanation_trace,
                }
                for hit in response.results
            ],
        }
        typer.echo(payload)
        return

    hits = service.search(query=query, top_k=top_k, route=route)

    typer.echo(
        [
            {
                "concept_id": hit.concept_id,
                "title": hit.title,
                "type": hit.concept_type,
                "score": round(hit.score, 4),
                "source": hit.source,
                "path": hit.path,
                "score_breakdown": hit.score_breakdown,
                "explanation_trace": hit.explanation_trace,
            }
            for hit in hits
        ]
    )


@app.command("agent-ask")
def agent_ask(question: str = typer.Argument(...), top_k: int = typer.Option(8, min=1, max=50)) -> None:
    """Run agentic Q&A over enterprise knowledge artifacts."""

    cfg = Settings()
    orchestrator = AgentOrchestrator.from_okf(
        okf_dir=cfg.resolve(cfg.okf_dir),
        vector_dir=cfg.resolve(cfg.vector_dir),
        embedding_fn=deterministic_embedding,
        llm=None,
    )
    response = orchestrator.ask(question=question, top_k=top_k)
    typer.echo(
        {
            "answer": response.answer,
            "citations": response.citations,
            "used_concepts": response.used_concepts,
            "tool_trace": response.tool_trace,
            "tool_calls": [asdict(call) for call in response.tool_calls],
            "evidence_summary": response.evidence_summary,
            "confidence": round(response.confidence, 4),
            "supported": response.supported,
            "unsupported_reason": response.unsupported_reason,
            "strategy": response.strategy,
        }
    )


@app.command("agent-eval")
def agent_eval(
    benchmark_path: Path = typer.Option(
        Path("examples/eval/agent_benchmark.json"),
        help="Benchmark JSON for enterprise agent evaluation.",
    ),
    top_k: int = typer.Option(8, min=1, max=50),
    output_json: Path | None = typer.Option(None, help="Optional path to write JSON report."),
) -> None:
    """Run benchmark evaluation for the agent workflow."""

    cfg = Settings()
    orchestrator = AgentOrchestrator.from_okf(
        okf_dir=cfg.resolve(cfg.okf_dir),
        vector_dir=cfg.resolve(cfg.vector_dir),
        embedding_fn=deterministic_embedding,
        llm=None,
    )
    harness = AgentEvaluationHarness(orchestrator)
    cases = harness.load_cases(benchmark_path)
    report = harness.run(cases=cases, top_k=top_k)
    payload = report.to_dict()

    if output_json is not None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("serve")
def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Serve FastAPI runtime for ingestion/retrieval/agent endpoints."""

    uvicorn.run(create_app(Settings()), host=host, port=port, log_level="info")


if __name__ == "__main__":
    app()

"""Typer CLI entrypoint for Enterprise OKF AI Hub."""

import asyncio
from pathlib import Path

import typer
import uvicorn
from loguru import logger

from okfhub.api import create_app
from okfhub.datasets import SyntheticEnterpriseCorpus
from okfhub.embeddings import ChromaConceptStore, EmbeddingPipeline
from okfhub.extraction import KnowledgeExtractor
from okfhub.graph import Neo4jGraphStore, export_pyvis_graph
from okfhub.ingestion import IngestionService
from okfhub.io import read_model_list, write_json, write_model_list
from okfhub.llm import OllamaClient
from okfhub.logging_config import configure_logging
from okfhub.models import DocumentChunk, ExtractedConcept
from okfhub.okf import OKFBundleGenerator, OKFBundleLoader
from okfhub.pipeline import EnterprisePipeline
from okfhub.settings import Settings
from okfhub.validators import OKFValidator

app = typer.Typer(help="Enterprise OKF AI Hub CLI")
agent_app = typer.Typer(help="Agent commands")
graph_app = typer.Typer(help="Graph commands")
corpus_app = typer.Typer(help="Synthetic corpus commands")
docs_app = typer.Typer(help="Documentation commands")
eval_app = typer.Typer(help="Evaluation commands")

app.add_typer(agent_app, name="agent")
app.add_typer(graph_app, name="graph")
app.add_typer(corpus_app, name="corpus")
app.add_typer(docs_app, name="docs")
app.add_typer(eval_app, name="eval")


@app.callback()
def _main() -> None:
    configure_logging()


def _settings() -> Settings:
    return Settings()


@app.command("run")
def run_pipeline(
    source_root: Path = typer.Option(Path("data/raw"), exists=True),
    okf_root: Path = typer.Option(Path("okf_bundle")),
) -> None:
    """Run end-to-end pipeline."""

    pipeline = EnterprisePipeline(_settings())
    result = asyncio.run(pipeline.run(source_root=source_root, okf_root=okf_root))
    typer.echo(str(result))


@app.command("ingest")
def ingest(
    source_root: Path = typer.Option(Path("data/raw"), exists=True),
    output: Path = typer.Option(Path("artifacts/chunks.json")),
) -> None:
    """Ingest and normalize source docs into chunks."""

    service = IngestionService(_settings())
    chunks = service.ingest_directory(source_root)
    write_model_list(output, chunks)
    typer.echo(f"Wrote {len(chunks)} chunks to {output}")


@app.command("extract")
def extract(
    chunks_path: Path = typer.Option(Path("artifacts/chunks.json"), exists=True),
    output: Path = typer.Option(Path("artifacts/concepts.json")),
) -> None:
    """Extract concepts from chunk artifacts."""

    chunks = read_model_list(chunks_path, DocumentChunk)
    extractor = KnowledgeExtractor(OllamaClient(_settings()))
    concepts = asyncio.run(extractor.extract(chunks))
    write_model_list(output, concepts)
    typer.echo(f"Wrote {len(concepts)} concepts to {output}")


@app.command("generate")
def generate(
    concepts_path: Path = typer.Option(Path("artifacts/concepts.json"), exists=True),
    okf_root: Path = typer.Option(Path("okf_bundle")),
) -> None:
    """Generate OKF bundle from extracted concepts."""

    concepts = read_model_list(concepts_path, ExtractedConcept)
    docs = OKFBundleGenerator(okf_root).generate(concepts)
    typer.echo(f"Generated {len(docs)} concept files under {okf_root}")


@app.command("validate")
def validate(okf_root: Path = typer.Option(Path("okf_bundle"), exists=True)) -> None:
    """Validate OKF bundle."""

    report = OKFValidator().validate(okf_root)
    typer.echo(report.model_dump_json(indent=2))


@app.command("embed")
def embed(okf_root: Path = typer.Option(Path("okf_bundle"), exists=True)) -> None:
    """Generate and persist concept embeddings."""

    cfg = _settings()
    docs = OKFBundleLoader().load(okf_root)
    pipeline = EmbeddingPipeline(
        ollama=OllamaClient(cfg),
        store=ChromaConceptStore(cfg.chroma_persist_directory),
    )
    asyncio.run(pipeline.index_documents(docs))
    typer.echo(f"Indexed embeddings for {len(docs)} concepts")


@app.command("query")
def query(question: str = typer.Argument(...), top_k: int = typer.Option(8)) -> None:
    """Run direct QA retrieval endpoint."""

    answer = asyncio.run(EnterprisePipeline(_settings()).query(question=question, top_k=top_k))
    typer.echo(answer.model_dump_json(indent=2))


@agent_app.command("ask")
def agent_ask(question: str = typer.Argument(...)) -> None:
    """Run full LangGraph agent query."""

    answer = asyncio.run(EnterprisePipeline(_settings()).agent_query(question=question))
    typer.echo(answer.model_dump_json(indent=2))


@graph_app.command("build")
def graph_build(okf_root: Path = typer.Option(Path("okf_bundle"), exists=True)) -> None:
    """Build Neo4j graph and static HTML visualization."""

    cfg = _settings()
    docs = OKFBundleLoader().load(okf_root)

    graph = Neo4jGraphStore(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
    try:
        graph.ensure_schema()
        graph.upsert_documents(docs)
    finally:
        graph.close()

    output = Path("knowledge_graph/graph.html")
    export_pyvis_graph(docs, output)
    typer.echo(f"Graph indexed and visualization written to {output}")


@graph_app.command("neighbors")
def graph_neighbors(concept_id: str = typer.Argument(...), depth: int = typer.Option(1)) -> None:
    """Fetch graph neighbors from Neo4j."""

    cfg = _settings()
    graph = Neo4jGraphStore(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
    try:
        neighbors = graph.neighbors(concept_id, depth=depth)
    finally:
        graph.close()

    write_json(Path("artifacts/neighbors.json"), [n.__dict__ for n in neighbors])
    typer.echo(f"Found {len(neighbors)} neighbors (saved to artifacts/neighbors.json)")


@corpus_app.command("generate")
def generate_corpus(output_root: Path = typer.Option(Path("data/raw"))) -> None:
    """Generate realistic synthetic enterprise corpus."""

    files = SyntheticEnterpriseCorpus(output_root).generate()
    typer.echo(f"Generated {len(files)} source documents under {output_root}")


@app.command("diff")
def diff(old_root: Path = typer.Argument(..., exists=True), new_root: Path = typer.Argument(..., exists=True)) -> None:
    """Compare two OKF bundle versions."""

    report = EnterprisePipeline(_settings()).diff_bundles(old_root=old_root, new_root=new_root)
    typer.echo(report.model_dump_json(indent=2))


@docs_app.command("generate")
def docs_generate(
    okf_root: Path = typer.Option(Path("okf_bundle"), exists=True),
    output_dir: Path = typer.Option(Path("docs/generated")),
) -> None:
    """Generate documentation artifacts from current OKF bundle."""

    files = EnterprisePipeline(_settings()).generate_docs(okf_root=okf_root, output_dir=output_dir)
    typer.echo(f"Generated {len(files)} documentation files under {output_dir}")


@eval_app.command("run")
def eval_run(
    dataset_path: Path = typer.Option(Path("examples/eval/gold_qa.json"), exists=True),
    mode: str = typer.Option("agent"),
    top_k: int = typer.Option(8),
    output: Path = typer.Option(Path("artifacts/evaluation_report.json")),
) -> None:
    """Run gold-set evaluation and write report JSON."""

    pipeline = EnterprisePipeline(_settings())
    report = asyncio.run(
        pipeline.evaluate(dataset_path=dataset_path, mode=mode, top_k=top_k)
    )
    write_json(output, report.model_dump(mode="json"))
    typer.echo(
        "Evaluation complete "
        f"(examples={report.summary.total_examples}, recall@k={report.summary.avg_recall_at_k:.3f}, "
        f"mrr={report.summary.avg_mrr:.3f}) -> {output}"
    )


@eval_app.command("gate")
def eval_gate(
    baseline_report: Path = typer.Option(..., exists=True),
    current_report: Path = typer.Option(..., exists=True),
    min_recall_delta: float = typer.Option(-0.02),
    min_mrr_delta: float = typer.Option(-0.02),
    min_faithfulness_delta: float = typer.Option(-0.15),
) -> None:
    """Run regression gate between baseline and current evaluation reports."""

    pipeline = EnterprisePipeline(_settings())
    verdict = pipeline.evaluate_gate(
        baseline_report_path=baseline_report,
        current_report_path=current_report,
        min_recall_delta=min_recall_delta,
        min_mrr_delta=min_mrr_delta,
        min_faithfulness_delta=min_faithfulness_delta,
    )
    typer.echo(str(verdict))


@app.command("serve")
def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run FastAPI service."""

    uvicorn.run(create_app(_settings()), host=host, port=port, log_level="info")


if __name__ == "__main__":
    logger.info("Starting OKF Hub CLI")
    app()

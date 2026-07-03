"""FastAPI application for the Enterprise OKF platform."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from okfhub.graph import Neo4jGraphStore
from okfhub.okf import OKFBundleLoader
from okfhub.pipeline import EnterprisePipeline
from okfhub.settings import Settings


class RunPipelineRequest(BaseModel):
    """Request body for running pipeline."""

    source_root: str
    okf_root: str | None = None


class ValidateRequest(BaseModel):
    """Request body for validation endpoint."""

    okf_root: str | None = None


class QueryRequest(BaseModel):
    """Request body for QA endpoints."""

    question: str = Field(min_length=3)
    top_k: int | None = None


class DiffRequest(BaseModel):
    """Request body for bundle diff endpoint."""

    old_root: str
    new_root: str


class DocsGenerateRequest(BaseModel):
    """Request body for docs generation endpoint."""

    okf_root: str | None = None
    output_dir: str = "docs/generated"


class EvalRunRequest(BaseModel):
    """Request body for evaluation run endpoint."""

    dataset_path: str
    mode: str = "agent"
    top_k: int = 8


class EvalGateRequest(BaseModel):
    """Request body for evaluation gate endpoint."""

    baseline_report_path: str
    current_report_path: str
    min_recall_delta: float = -0.02
    min_mrr_delta: float = -0.02
    min_faithfulness_delta: float = -0.15


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create configured FastAPI app instance."""

    cfg = settings or Settings()
    pipeline = EnterprisePipeline(cfg)
    app = FastAPI(title="Enterprise OKF AI Hub", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/pipeline/run")
    async def run_pipeline(payload: RunPipelineRequest) -> dict[str, object]:
        source_root = Path(payload.source_root)
        if not source_root.exists():
            raise HTTPException(status_code=404, detail=f"Source root not found: {source_root}")

        okf_root = Path(payload.okf_root) if payload.okf_root else None
        return await pipeline.run(source_root=source_root, okf_root=okf_root)

    @app.post("/validate")
    async def validate(payload: ValidateRequest) -> dict[str, object]:
        report = pipeline.validate(okf_root=Path(payload.okf_root) if payload.okf_root else None)
        return report.model_dump()

    @app.post("/query")
    async def query(payload: QueryRequest) -> dict[str, object]:
        answer = await pipeline.query(payload.question, payload.top_k)
        return answer.model_dump()

    @app.post("/agent/query")
    async def agent_query(payload: QueryRequest) -> dict[str, object]:
        answer = await pipeline.agent_query(payload.question)
        return answer.model_dump()

    @app.post("/diff")
    async def diff(payload: DiffRequest) -> dict[str, object]:
        report = pipeline.diff_bundles(old_root=Path(payload.old_root), new_root=Path(payload.new_root))
        return report.model_dump()

    @app.post("/docs/generate")
    async def docs_generate(payload: DocsGenerateRequest) -> dict[str, object]:
        okf_root = Path(payload.okf_root) if payload.okf_root else cfg.okf_root
        output_dir = Path(payload.output_dir)
        files = pipeline.generate_docs(okf_root=okf_root, output_dir=output_dir)
        return {"generated_files": [file.as_posix() for file in files]}

    @app.post("/eval/run")
    async def eval_run(payload: EvalRunRequest) -> dict[str, object]:
        report = await pipeline.evaluate(
            dataset_path=Path(payload.dataset_path),
            mode=payload.mode,
            top_k=payload.top_k,
        )
        return report.model_dump()

    @app.post("/eval/gate")
    async def eval_gate(payload: EvalGateRequest) -> dict[str, object]:
        result = pipeline.evaluate_gate(
            baseline_report_path=Path(payload.baseline_report_path),
            current_report_path=Path(payload.current_report_path),
            min_recall_delta=payload.min_recall_delta,
            min_mrr_delta=payload.min_mrr_delta,
            min_faithfulness_delta=payload.min_faithfulness_delta,
        )
        return result

    @app.get("/concept/{concept_id}")
    async def get_concept(concept_id: str) -> dict[str, object]:
        docs = OKFBundleLoader().load(cfg.okf_root)
        match = next((doc for doc in docs if doc.concept_id == concept_id), None)
        if match is None:
            raise HTTPException(status_code=404, detail="Concept not found")

        return {
            "concept_id": match.concept_id,
            "relative_path": match.relative_path,
            "frontmatter": match.frontmatter.model_dump(),
            "body": match.body,
            "links": match.links,
        }

    @app.get("/graph/neighbors/{concept_id}")
    async def graph_neighbors(concept_id: str, depth: int = 1, limit: int = 25) -> dict[str, object]:
        graph = Neo4jGraphStore(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
        try:
            neighbors = graph.neighbors(concept_id=concept_id, depth=depth, limit=limit)
            return {
                "concept_id": concept_id,
                "neighbors": [neighbor.__dict__ for neighbor in neighbors],
            }
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        finally:
            graph.close()

    return app


app = create_app()

"""End-to-end pipeline orchestration for ingestion, OKF, indexing, and QA."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from okfhub.agent import EnterpriseKnowledgeAgent
from okfhub.diffing import OKFDiffService
from okfhub.docs_generator import DocumentationGenerator
from okfhub.embeddings import ChromaConceptStore, EmbeddingPipeline
from okfhub.evaluation import EvaluationService
from okfhub.extraction import KnowledgeExtractor
from okfhub.graph import Neo4jGraphStore, export_pyvis_graph
from okfhub.ingestion import IngestionService
from okfhub.io import read_json
from okfhub.llm import OllamaClient
from okfhub.models import AgentAnswer, DiffReport, EvaluationReport, ValidationReport
from okfhub.okf import OKFBundleGenerator, OKFBundleLoader
from okfhub.retrieval import HybridRetriever
from okfhub.settings import Settings
from okfhub.validators import OKFValidator


class EnterprisePipeline:
    """Facade for executing OKF platform workflows."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._ollama = OllamaClient(settings)

    async def run(self, source_root: Path, okf_root: Path | None = None) -> dict[str, object]:
        """Execute ingestion -> extraction -> OKF generation -> validation -> indexing."""

        bundle_root = okf_root or self._settings.okf_root

        ingestion = IngestionService(self._settings)
        chunks = ingestion.ingest_directory(source_root)

        extractor = KnowledgeExtractor(self._ollama)
        concepts = await extractor.extract(chunks)

        generator = OKFBundleGenerator(bundle_root)
        generated_docs = generator.generate(concepts)

        validator = OKFValidator()
        validation_report = validator.validate(bundle_root)

        loader = OKFBundleLoader()
        docs = loader.load(bundle_root)

        graph_status = self._index_graph(docs)
        await self._index_embeddings(docs)
        self._export_graph_visual(docs)

        return {
            "chunks": len(chunks),
            "concepts": len(concepts),
            "generated_docs": len(generated_docs),
            "validation": validation_report.model_dump(),
            "graph": graph_status,
        }

    def validate(self, okf_root: Path | None = None) -> ValidationReport:
        """Validate bundle and return report."""

        root = okf_root or self._settings.okf_root
        validator = OKFValidator()
        return validator.validate(root)

    async def query(self, question: str, top_k: int | None = None) -> AgentAnswer:
        """Hybrid retrieval QA without full agent tooling."""

        docs = OKFBundleLoader().load(self._settings.okf_root)
        store = ChromaConceptStore(self._settings.chroma_persist_directory)
        graph = self._new_graph_store_or_none()

        retriever = HybridRetriever(docs=docs, vector_store=store, ollama=self._ollama, graph_store=graph)
        hits = await retriever.search(question, top_k=top_k or self._settings.retrieval_top_k)

        if graph is not None:
            graph.close()

        if not hits:
            return AgentAnswer(
                answer="I could not find grounded evidence in the knowledge base.",
                citations=[],
                used_concepts=[],
                confidence=0.0,
                abstained=True,
            )

        context = "\n\n".join(
            f"[{hit.concept_id}] {hit.content[:1400]}" for hit in hits[:6]
        )
        prompt = (
            "Answer the question using only the provided context. "
            "If evidence is insufficient, state uncertainty.\n\n"
            f"Question:\n{question}\n\n"
            f"Context:\n{context}"
        )
        answer = await self._ollama.chat_text(prompt)

        return AgentAnswer(
            answer=answer,
            citations=[hit.source_path for hit in hits[:6]],
            used_concepts=[hit.concept_id for hit in hits[:6]],
            confidence=min(1.0, sum(h.score for h in hits[:3]) / 3),
            abstained=False,
        )

    async def agent_query(self, question: str) -> AgentAnswer:
        """Full agent query using LangGraph workflow and tools."""

        docs = OKFBundleLoader().load(self._settings.okf_root)
        store = ChromaConceptStore(self._settings.chroma_persist_directory)
        graph = self._new_graph_store_or_none()

        retriever = HybridRetriever(docs=docs, vector_store=store, ollama=self._ollama, graph_store=graph)
        agent = EnterpriseKnowledgeAgent(
            retriever=retriever,
            ollama=self._ollama,
            documents=docs,
            graph_store=graph,
        )
        answer = await agent.ask(question)

        if graph is not None:
            graph.close()

        return answer

    async def evaluate(self, dataset_path: Path, mode: str = "agent", top_k: int = 8) -> EvaluationReport:
        """Run gold-set QA evaluation with retrieval and optional LLM judge metrics."""

        service = EvaluationService(engine=self, ollama=self._ollama)
        return await service.run(dataset_path=dataset_path, mode=mode, top_k=top_k)

    def evaluate_gate(
        self,
        baseline_report_path: Path,
        current_report_path: Path,
        min_recall_delta: float = -0.02,
        min_mrr_delta: float = -0.02,
        min_faithfulness_delta: float = -0.15,
    ) -> dict[str, object]:
        """Compare two evaluation reports and return a regression gate verdict."""

        baseline = EvaluationReport.model_validate(read_json(baseline_report_path))
        current = EvaluationReport.model_validate(read_json(current_report_path))
        service = EvaluationService(engine=self, ollama=self._ollama)
        return service.compare_reports(
            baseline=baseline,
            current=current,
            min_recall_delta=min_recall_delta,
            min_mrr_delta=min_mrr_delta,
            min_faithfulness_delta=min_faithfulness_delta,
        )

    def diff_bundles(self, old_root: Path, new_root: Path) -> DiffReport:
        """Compare two OKF bundle versions."""

        return OKFDiffService().diff(old_root=old_root, new_root=new_root)

    def generate_docs(self, okf_root: Path, output_dir: Path) -> list[Path]:
        """Generate documentation artifacts from current bundle state."""

        return DocumentationGenerator().generate(okf_root=okf_root, output_dir=output_dir)

    def _index_graph(self, docs) -> str:
        graph = self._new_graph_store_or_none()
        if graph is None:
            return "Neo4j unavailable or misconfigured"

        try:
            graph.ensure_schema()
            graph.upsert_documents(docs)
            return "Indexed"
        except Exception as exc:  # noqa: BLE001
            logger.warning("Graph indexing failed: {}", exc)
            return f"Failed: {exc}"
        finally:
            graph.close()

    async def _index_embeddings(self, docs) -> None:
        store = ChromaConceptStore(self._settings.chroma_persist_directory)
        pipeline = EmbeddingPipeline(self._ollama, store)
        await pipeline.index_documents(docs)

    def _export_graph_visual(self, docs) -> None:
        output = Path("knowledge_graph/graph.html")
        export_pyvis_graph(docs, output)

    def _new_graph_store_or_none(self) -> Neo4jGraphStore | None:
        try:
            return Neo4jGraphStore(
                uri=self._settings.neo4j_uri,
                user=self._settings.neo4j_user,
                password=self._settings.neo4j_password,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Neo4j store initialization failed: {}", exc)
            return None

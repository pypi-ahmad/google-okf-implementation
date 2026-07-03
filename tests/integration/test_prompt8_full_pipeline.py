from __future__ import annotations

from pathlib import Path

from enterprise_okf_ai.agent import AgentOrchestrator
from enterprise_okf_ai.core.embeddings import deterministic_embedding
from enterprise_okf_ai.graph import GraphService
from enterprise_okf_ai.ingestion import IngestionService
from enterprise_okf_ai.okf import OKFBundleGenerator
from enterprise_okf_ai.retrieval import RetrievalService
from enterprise_okf_ai.validators import BundleValidator
from ingest.parser import DocumentParser
from vector_db.indexer import OKFVectorIndexer


def test_prompt8_end_to_end_pipeline_smoke(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw_docs"
    okf_dir = tmp_path / "okf_bundle"
    vector_dir = tmp_path / "vector_store"
    graph_dir = tmp_path / "graph"

    (raw_dir / "apis").mkdir(parents=True, exist_ok=True)
    (raw_dir / "datasets").mkdir(parents=True, exist_ok=True)
    (raw_dir / "metrics").mkdir(parents=True, exist_ok=True)
    (raw_dir / "playbooks").mkdir(parents=True, exist_ok=True)
    (raw_dir / "tables").mkdir(parents=True, exist_ok=True)

    (raw_dir / "apis" / "orders_api.md").write_text(
        "# Orders API\nPATCH /v2/orders/{order_id} updates order status.\nDependencies:\n- Customer Profile Dataset\n",
        encoding="utf-8",
    )
    (raw_dir / "datasets" / "customer_profile.md").write_text(
        "# Customer Profile Dataset\nCanonical customer profile records.\n",
        encoding="utf-8",
    )
    (raw_dir / "metrics" / "mau.md").write_text(
        "# Monthly Active Users\nCOUNT(DISTINCT customer_id) in analytics month.\n",
        encoding="utf-8",
    )
    (raw_dir / "playbooks" / "payment_failure.md").write_text(
        "# Payment Failure Playbook\nTrigger when error rate > 3% for 5 minutes.\n",
        encoding="utf-8",
    )
    (raw_dir / "tables" / "orders_fact.csv").write_text(
        "column,type,description\norder_id,string,Order identifier\ncustomer_id,string,Customer identifier\n",
        encoding="utf-8",
    )

    ingestion = IngestionService(parser=DocumentParser())
    parsed_docs = ingestion.ingest(raw_dir, recursive=True, fail_fast=True)
    assert len(parsed_docs) == 5

    build_report = OKFBundleGenerator(output_dir=okf_dir, source_dir=raw_dir).build(parsed_docs)
    assert build_report.concept_count >= 4

    validation = BundleValidator().validate(okf_dir)
    assert validation.passed is True

    graph_service = GraphService(okf_dir)
    graph_artifacts = graph_service.build_and_export(
        json_path=graph_dir / "graph.json",
        html_path=graph_dir / "graph.html",
        graphml_path=graph_dir / "graph.graphml",
    )
    assert graph_artifacts.nodes >= 4
    assert graph_artifacts.edges >= 1

    index_stats = OKFVectorIndexer(okf_dir=okf_dir, persist_dir=vector_dir, embedding_fn=deterministic_embedding).index()
    assert index_stats["chunks_indexed"] >= 1

    retrieval = RetrievalService.from_okf(
        okf_dir=okf_dir,
        vector_dir=vector_dir,
        embedding_fn=deterministic_embedding,
        include_graph=True,
    )
    retrieval_response = retrieval.search_with_trace(
        query="Which API updates order status?",
        top_k=5,
        route="auto",
    )
    assert retrieval_response.results
    assert retrieval_response.router_trace

    orchestrator = AgentOrchestrator.from_okf(
        okf_dir=okf_dir,
        vector_dir=vector_dir,
        embedding_fn=deterministic_embedding,
        llm=None,
    )
    agent_response = orchestrator.ask(
        question="Which API updates orders and what dataset is linked?",
        top_k=6,
    )
    assert agent_response.supported is True
    assert agent_response.citations
    assert agent_response.used_concepts

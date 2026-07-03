"""Generate a polished end-to-end tutorial notebook for enterprise OKF AI."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path


def _md(text: str) -> dict[str, object]:
    normalized = textwrap.dedent(text).strip("\n")
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in normalized.splitlines()],
    }


def _code(code: str) -> dict[str, object]:
    normalized = textwrap.dedent(code).strip("\n")
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in normalized.splitlines()],
    }


def build_notebook() -> dict[str, object]:
    """Build tutorial notebook payload."""

    cells: list[dict[str, object]] = []

    cells.append(
        _md(
            """
            # Enterprise Knowledge Hub with OKF + Hybrid Retrieval + Agentic QA

            This tutorial walks through a production-style knowledge engineering pipeline.
            It turns fragmented enterprise docs into a validated OKF bundle, builds graph
            and vector indexes, and answers questions through a grounded agent.

            ## You will build

            1. Ingestion and normalization across mixed document types.
            2. OKF bundle generation (Markdown + YAML frontmatter).
            3. Validation and bundle health diagnostics.
            4. Knowledge graph construction and export.
            5. Hybrid retrieval (vector + BM25 + graph).
            6. Agentic execution with tool traces and citations.
            7. Retrieval and agent benchmark evaluation.
            """
        )
    )

    cells.append(
        _md(
            """
            ## 1. The Problem: Enterprise Knowledge is Fragmented

            In real organizations, context is distributed across APIs, runbooks,
            metrics docs, data dictionaries, and incident notes. A plain
            "chat with docs" setup struggles when:

            - entities are duplicated across sources,
            - links between concepts are implicit,
            - ownership and dependency questions require traversal, not just similarity.

            We need a **knowledge lifecycle** rather than a single retrieval step.
            """
        )
    )

    cells.append(
        _md(
            """
            ## 2. Why Raw-Document RAG Is Not Enough

            Raw-document RAG can be useful, but it often misses:

            - canonical concept identity (`orders-api` vs `orders_api_duplicate`),
            - typed metadata (`type=metric`, `owner`, `sources`, `relationships`),
            - graph-structured reasoning for dependency and ownership questions.

            The Open Knowledge Format (OKF) addresses this by standardizing knowledge
            as markdown files with minimal YAML frontmatter (the spec requires only
            a non-empty `type`). This repository then layers a stricter enterprise
            profile on top (extra required fields + explicit `relationships`) so it
            can build deterministic graphs and validation gates.
            """
        )
    )

    cells.append(
        _md(
            """
            ## 3. Environment Setup

            This notebook locates the project root automatically, adds `src/`
            to `PYTHONPATH`, and prepares a clean tutorial workspace under
            `artifacts/tutorial/`.
            """
        )
    )

    cells.append(
        _code(
            """
            from __future__ import annotations

            import json
            import shutil
            import sys
            from pathlib import Path

            def find_project_root(start: Path) -> Path:
                for candidate in [start, *start.parents]:
                    if (candidate / "pyproject.toml").exists():
                        return candidate
                raise RuntimeError("Could not locate project root containing pyproject.toml")

            PROJECT_ROOT = find_project_root(Path.cwd())
            SRC_PATH = PROJECT_ROOT / "src"
            if str(SRC_PATH) not in sys.path:
                sys.path.insert(0, str(SRC_PATH))

            WORK_DIR = PROJECT_ROOT / "artifacts" / "tutorial"
            RAW_DIR = PROJECT_ROOT / "examples" / "enterprise_docs"
            OKF_DIR = WORK_DIR / "okf_bundle"
            VECTOR_DIR = WORK_DIR / "vector_store"
            GRAPH_DIR = WORK_DIR / "graph"

            if WORK_DIR.exists():
                shutil.rmtree(WORK_DIR)
            WORK_DIR.mkdir(parents=True, exist_ok=True)
            GRAPH_DIR.mkdir(parents=True, exist_ok=True)

            {
                "project_root": str(PROJECT_ROOT),
                "raw_docs": str(RAW_DIR),
                "workspace": str(WORK_DIR),
            }
            """
        )
    )

    cells.append(
        _md(
            """
            ## 4. Ingestion and Normalization

            We parse heterogeneous docs into a common internal object model with:

            - unified text content,
            - metadata and provenance,
            - headings, sections, tables,
            - section-aware chunks for downstream processing.
            """
        )
    )

    cells.append(
        _code(
            """
            import pandas as pd

            from enterprise_okf_ai.ingestion import IngestionService
            from ingest.parser import DocumentParser

            parser = DocumentParser(chunk_size_chars=1000, chunk_overlap_chars=120)
            ingestion = IngestionService(parser=parser)
            parsed_docs = ingestion.ingest(RAW_DIR, recursive=True, fail_fast=True)

            pd.DataFrame(
                [
                    {
                        "file": doc.file_path.relative_to(RAW_DIR).as_posix(),
                        "file_type": doc.file_type,
                        "sections": len(doc.sections),
                        "tables": len(doc.tables),
                        "chunks": len(doc.chunks),
                        "author": doc.metadata.get("author"),
                    }
                    for doc in parsed_docs
                ]
            ).sort_values("file")
            """
        )
    )

    cells.append(
        _md(
            """
            ## 5. OKF Bundle Generation

            Next we compile normalized documents into an OKF-shaped bundle:

            - stable concept directories (`apis/`, `datasets/`, `metrics/`, `playbooks/`, `tables/`, `glossary/`),
            - markdown concept files with YAML frontmatter (`type` required by the spec),
            - additional enterprise-required metadata and explicit relationships (repo convention),
            - deduplicated concept mapping.
            """
        )
    )

    cells.append(
        _code(
            """
            from enterprise_okf_ai.okf import OKFBundleGenerator

            generator = OKFBundleGenerator(output_dir=OKF_DIR, source_dir=RAW_DIR)
            build_report = generator.build(parsed_docs)

            bundle_files = sorted(path.relative_to(OKF_DIR).as_posix() for path in OKF_DIR.rglob("*.md"))
            {
                "concept_count": build_report.concept_count,
                "deduplicated_concepts": build_report.deduplicated_concepts,
                "concepts_by_type": build_report.concepts_by_type,
                "bundle_files": bundle_files,
            }
            """
        )
    )

    cells.append(
        _code(
            """
            # Inspect one generated concept page.
            sample_page = OKF_DIR / "apis" / "orders-api.md"
            print(sample_page.read_text(encoding="utf-8")[:1800])
            """
        )
    )

    cells.append(
        _md(
            """
            ## 6. Validation and Bundle Health

            A knowledge compiler must be linted like code. We run strict checks for:

            - invalid YAML frontmatter,
            - missing mandatory fields,
            - broken internal links,
            - duplicate concept definitions,
            - orphan documents,
            - circular references.
            """
        )
    )

    cells.append(
        _code(
            """
            from enterprise_okf_ai.reports import BundleHealthReporter
            from enterprise_okf_ai.validators import BundleValidator

            validation_report = BundleValidator().validate(OKF_DIR)
            health_report = BundleHealthReporter().generate(OKF_DIR)

            {
                "validation_passed": validation_report.passed,
                "validation_stats": validation_report.stats,
                "graph_stats": health_report.graph_stats,
                "relation_counts": health_report.relation_counts,
            }
            """
        )
    )

    cells.append(
        _md(
            """
            ## 7. Knowledge Graph Construction

            We build a directed graph from markdown links and relationship metadata,
            then export it for downstream retrieval and visualization.
            """
        )
    )

    cells.append(
        _code(
            """
            from enterprise_okf_ai.graph import GraphService

            graph_service = GraphService(OKF_DIR)
            graph_artifacts = graph_service.build_and_export(
                json_path=GRAPH_DIR / "graph.json",
                html_path=GRAPH_DIR / "graph.html",
                graphml_path=GRAPH_DIR / "graph.graphml",
            )
            graph = graph_service.build()

            {
                "nodes": graph_artifacts.nodes,
                "edges": graph_artifacts.edges,
                "json_path": graph_artifacts.json_path.as_posix(),
                "html_path": graph_artifacts.html_path.as_posix(),
                "graphml_path": graph_artifacts.graphml_path.as_posix() if graph_artifacts.graphml_path else None,
                "neighbors_of_orders_api": graph_service.neighbors("api:orders-api", depth=1, direction="both"),
            }
            """
        )
    )

    cells.append(
        _md(
            """
            ## 8. Hybrid Retrieval (Vector + BM25 + Graph)

            We index the bundle into Chroma and run retrieval with route-aware orchestration:

            - `vector`: semantic-heavy,
            - `keyword`: lexical-heavy,
            - `graph`: relation traversal emphasis,
            - `hybrid`: weighted ensemble,
            - `auto`: route selected from query intent.
            """
        )
    )

    cells.append(
        _code(
            """
            from enterprise_okf_ai.core.embeddings import deterministic_embedding
            from enterprise_okf_ai.retrieval import RetrievalService
            from vector_db.indexer import OKFVectorIndexer

            indexer = OKFVectorIndexer(okf_dir=OKF_DIR, persist_dir=VECTOR_DIR, embedding_fn=deterministic_embedding)
            index_stats = indexer.index()

            retrieval = RetrievalService.from_okf(
                okf_dir=OKF_DIR,
                vector_dir=VECTOR_DIR,
                embedding_fn=deterministic_embedding,
                include_graph=True,
            )

            retrieval_response = retrieval.search_with_trace(
                query="Which API updates order status and what dataset does it depend on?",
                top_k=5,
                route="auto",
            )

            {
                "index_stats": index_stats,
                "route": retrieval_response.route,
                "router_trace": retrieval_response.router_trace,
                "top_results": [
                    {
                        "concept_id": hit.concept_id,
                        "type": hit.concept_type,
                        "score": round(hit.score, 4),
                        "source": hit.source,
                    }
                    for hit in retrieval_response.results[:5]
                ],
            }
            """
        )
    )

    cells.append(
        _md(
            """
            ## 9. Agent Execution with Tool Traces

            The agent orchestrates tool calls over:

            1. OKF keyword search
            2. vector/hybrid retrieval
            3. graph traversal
            4. document reads
            5. evidence summarization

            It returns grounded answers with citations, confidence, and unsupported-answer safeguards.
            """
        )
    )

    cells.append(
        _code(
            """
            from enterprise_okf_ai.agent import AgentOrchestrator

            orchestrator = AgentOrchestrator.from_okf(
                okf_dir=OKF_DIR,
                vector_dir=VECTOR_DIR,
                embedding_fn=deterministic_embedding,
                llm=None,  # deterministic local heuristic mode for tutorial reproducibility
            )

            agent_response = orchestrator.ask(
                "Show the owner and dependencies for Orders API, and mention the related metric.",
                top_k=8,
            )

            {
                "answer": agent_response.answer,
                "supported": agent_response.supported,
                "confidence": round(agent_response.confidence, 4),
                "strategy": agent_response.strategy,
                "citations": agent_response.citations,
                "used_concepts": agent_response.used_concepts,
                "tool_calls": [call.tool_name for call in agent_response.tool_calls],
            }
            """
        )
    )

    cells.append(
        _md(
            """
            ## 10. Evaluation

            We run:

            - retrieval benchmark metrics (`recall@k`, `MRR`, `answer support`),
            - agent benchmark metrics (concept recall, answer support, abstain accuracy).
            """
        )
    )

    cells.append(
        _code(
            """
            from enterprise_okf_ai.agent import AgentEvaluationHarness
            from enterprise_okf_ai.retrieval import RetrievalBenchmarkSample, RetrievalEvaluator

            retrieval_evaluator = RetrievalEvaluator(retrieval.router)
            retrieval_eval_report = retrieval_evaluator.evaluate(
                samples=[
                    RetrievalBenchmarkSample(
                        query="Which API updates order status?",
                        expected_concept_ids=["apis/orders-api"],
                        support_terms=["order status", "PATCH /v2/orders/{order_id}"],
                        route="hybrid",
                    ),
                    RetrievalBenchmarkSample(
                        query="How is Monthly Active Users calculated?",
                        expected_concept_ids=["metrics/monthly-active-users"],
                        support_terms=["COUNT(DISTINCT customer_id)", "analytics month"],
                        route="auto",
                    ),
                ],
                top_k=5,
                use_graph_expansion=True,
            )

            agent_harness = AgentEvaluationHarness(orchestrator)
            benchmark_path = PROJECT_ROOT / "examples" / "eval" / "agent_benchmark.json"
            agent_cases = agent_harness.load_cases(benchmark_path)
            agent_eval_report = agent_harness.run(cases=agent_cases, top_k=8)

            {
                "retrieval_summary": {
                    "avg_recall_at_k": round(retrieval_eval_report.summary.avg_recall_at_k, 4),
                    "avg_mrr": round(retrieval_eval_report.summary.avg_mrr, 4),
                    "avg_answer_support": round(retrieval_eval_report.summary.avg_answer_support, 4),
                },
                "agent_summary": {
                    "total_cases": agent_eval_report.summary.total_cases,
                    "avg_concept_recall": round(agent_eval_report.summary.avg_concept_recall, 4),
                    "avg_answer_support": round(agent_eval_report.summary.avg_answer_support, 4),
                    "abstain_accuracy": round(agent_eval_report.summary.abstain_accuracy, 4),
                },
            }
            """
        )
    )

    cells.append(
        _md(
            """
            ## 11. What to Run Next

            - Use `enterprise-okf-ai serve` to expose FastAPI endpoints.
            - Use `make run-ui` for the Streamlit interface.
            - Replace deterministic embeddings and heuristic answering with your production embedding model and LLM.
            - Add this notebook execution to CI to keep the tutorial evergreen.
            """
        )
    )

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    notebook = build_notebook()
    output = Path("notebooks/tutorial.ipynb")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(notebook, indent=2), encoding="utf-8")
    print(f"Generated tutorial notebook at {output}")


if __name__ == "__main__":
    main()

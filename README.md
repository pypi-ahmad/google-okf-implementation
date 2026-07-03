# enterprise-okf-ai

Enterprise Knowledge Hub that converts fragmented enterprise documentation into an OKF-style knowledge bundle, validates it, builds a knowledge graph, indexes it for hybrid retrieval, and serves grounded agentic Q&A.

## Project Overview

This repository implements an end-to-end enterprise knowledge engineering workflow using Open Knowledge Format (OKF-style markdown + YAML frontmatter), retrieval-augmented generation, graph traversal, and tool-based agent orchestration.

It is built as a production-oriented Python project with:
- typed modules in `src/enterprise_okf_ai/`
- CLI (`enterprise-okf-ai`)
- FastAPI service
- Streamlit UI
- CI, tests, notebook validation, and release checklist

## Problem Statement

Enterprise knowledge is usually distributed across many formats and tools (API docs, runbooks, metrics docs, markdown, CSV schemas, incident pages). Raw-document RAG alone often fails on:
- dependency tracing
- ownership or relationship questions
- structured navigation across APIs, datasets, metrics, and playbooks

## Objectives

- Ingest heterogeneous documents into a normalized internal model.
- Generate a deterministic OKF-style markdown bundle.
- Validate bundle quality (schema, links, cycles, orphans, duplicates).
- Build a directed knowledge graph from links and relationships.
- Support hybrid retrieval (vector + BM25 + graph signals).
- Provide grounded Q&A with citations and unsupported-answer safeguards.
- Provide measurable evaluation artifacts for retrieval and agent quality.

## Architecture / Approach

```text
Raw Documents
  -> Ingestion + Normalization
  -> OKF Bundle Generation
  -> Validation + Health Reporting
  -> Knowledge Graph (NetworkX)
  -> Embeddings + Vector Index (Chroma)
  -> Hybrid Retrieval Router
  -> Tool-Calling Agent
  -> Evaluation + API/UI
```

Primary modules:
- `enterprise_okf_ai.ingestion`: parsing and normalization
- `enterprise_okf_ai.okf`: bundle generation
- `enterprise_okf_ai.validators`: strict OKF checks
- `enterprise_okf_ai.graph`: graph build/export
- `enterprise_okf_ai.retrieval`: router + metrics
- `enterprise_okf_ai.agent`: orchestration + evaluation
- `enterprise_okf_ai.api`: FastAPI runtime
- `enterprise_okf_ai.ui`: Streamlit app

Detailed architecture docs are in [docs/architecture.md](docs/architecture.md).

## Implementation Process

1. Parse source docs (`PDF`, `DOCX`, `Markdown`, `CSV`, `HTML`) with metadata preservation.
2. Extract deterministic concept candidates and deduplicate by stable slug/id.
3. Write strict concept markdown pages with required YAML frontmatter.
4. Validate bundle integrity (required fields, internal links, duplicates, cycles, orphans).
5. Build and export graph artifacts (`JSON`, `GraphML`, interactive `HTML`).
6. Index concept chunks in Chroma with idempotent update behavior.
7. Run retrieval routes (`auto`, `vector`, `keyword`, `graph`, `hybrid`) with score traces.
8. Run agent workflow with tools, evidence summary, confidence, and citations.
9. Evaluate retrieval and agent benchmarks.

## Setup and Installation

### Prerequisites

- Python 3.11+
- `uv`

### Install

```bash
uv sync --extra dev --frozen
cp .env.example .env
```

## Usage

### Core quality checks

```bash
make check
```

### Full real end-to-end run (strict)

```bash
make run-e2e
```

This runs ingestion, bundle generation, strict validation, graph export, vector indexing, retrieval, agent evaluation, and API endpoint checks.

### CLI examples

```bash
# Build OKF bundle from source docs
uv run enterprise-okf-ai build-okf examples/enterprise_docs artifacts/local_okf_bundle

# Validate OKF bundle
uv run enterprise-okf-ai okf-validate --okf-dir artifacts/local_okf_bundle

# Build graph artifacts
uv run enterprise-okf-ai graph-build --okf-dir artifacts/local_okf_bundle

# Hybrid retrieval
uv run enterprise-okf-ai retrieve-search "Which API updates order status?" --with-trace

# Agent question answering
uv run enterprise-okf-ai agent-ask "Which API updates order status and what does it depend on?"
```

### Runtime services

```bash
# FastAPI
make run-api

# Streamlit
make run-ui
```

### Handbook artifacts

```bash
make handbook-pdf
```

Outputs:
- `HANDBOOK.md`
- `HANDBOOK.pdf`

## Experiments / Workflow

Verified project workflow in this repository:

1. `make check`
- `ruff`, `mypy`, `pytest`, notebook validation.

2. `make run-e2e`
- Runs strict end-to-end pipeline on `examples/enterprise_docs`.
- Writes summary artifact: `artifacts/e2e_real_run/e2e_summary.json`.

3. Evaluation inputs
- Agent benchmark: `examples/eval/agent_benchmark.json`.

## Outputs / Results

From the latest strict E2E run in this workspace (`artifacts/e2e_real_run/e2e_summary.json`):

- Validation:
  - `validation_errors = 0`
  - `validation_warnings = 0`
  - `cycles = 0`, `orphans = 0`
- Graph:
  - `nodes = 9`, `edges = 17`
- Indexing:
  - `files_scanned = 9`, `chunks_indexed = 11`
- Retrieval/API:
  - retrieval route results returned (`result_count = 8`)
  - API statuses: health/retrieval/ask/evaluate all `200`
- Agent eval summary:
  - `total_cases = 4`
  - `avg_concept_recall = 1.0`
  - `avg_answer_support = 0.5`
  - `abstain_accuracy = 0.5`

## Limitations

- Default embeddings in local runs use deterministic fallback vectors, not production embedding providers.
- Agent abstention behavior still needs tuning (`abstain_accuracy = 0.5` in current benchmark).
- Current sample corpus is realistic but small; broader enterprise coverage requires more documents.
- Legacy compatibility package (`src/okfhub`) exists and may add cognitive overhead for new contributors.

## Future Improvements

- Improve unsupported-answer calibration and benchmark coverage.
- Add stronger reranking and section-aware retrieval scoring.
- Expand benchmark suite with domain-specific negative cases and drift tests.
- Add deployment profiles (containerized API/UI and infra manifests).
- Add continuous metric tracking across releases.

## References / Sources

Project-specific sources used in this repository:
- Google Cloud OKF overview: https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing
- OKF spec (GoogleCloudPlatform): https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
- Repository architecture notes: [docs/architecture.md](docs/architecture.md)
- OKF format notes: [docs/okf-format.md](docs/okf-format.md)
- Retrieval notes: [docs/retrieval.md](docs/retrieval.md)
- Agent notes: [docs/agent.md](docs/agent.md)
- Evaluation notes: [docs/evaluation.md](docs/evaluation.md)
- End-to-end evidence artifact: [artifacts/e2e_real_run/e2e_summary.json](artifacts/e2e_real_run/e2e_summary.json)

Official framework and tool documentation relevant to this implementation:
- `uv`: https://docs.astral.sh/uv/
- FastAPI: https://fastapi.tiangolo.com/
- Typer: https://typer.tiangolo.com/
- Pydantic: https://docs.pydantic.dev/
- LangChain: https://python.langchain.com/
- LangGraph: https://langchain-ai.github.io/langgraph/
- ChromaDB: https://docs.trychroma.com/
- NetworkX: https://networkx.org/documentation/stable/
- PyVis: https://pyvis.readthedocs.io/
- PyPDF: https://pypdf.readthedocs.io/
- python-docx: https://python-docx.readthedocs.io/
- Streamlit: https://docs.streamlit.io/
- pytest: https://docs.pytest.org/
- GitHub Actions: https://docs.github.com/actions

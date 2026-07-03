# enterprise-okf-ai

Enterprise Knowledge Hub that converts fragmented enterprise documentation into an OKF-style knowledge bundle, validates it, builds a knowledge graph, indexes content for hybrid retrieval, and serves grounded agentic Q&A.

## Project Status

`Beta` (`v0.1.0`): production-oriented architecture and validation gates are present, but agent abstention and benchmark depth still need improvement.

## Problem Statement

Enterprise knowledge is distributed across API docs, runbooks, metrics definitions, markdown notes, CSV schemas, and incident pages. Raw-document RAG alone often fails on:
- dependency tracing
- ownership and relationship reasoning
- structured navigation across APIs, datasets, metrics, tables, and playbooks

## Objectives

- Normalize heterogeneous documents into a stable internal model.
- Generate deterministic OKF-style markdown bundles.
- Validate knowledge integrity (metadata, links, duplicates, cycles, orphans).
- Build a graph-aware retrieval layer (vector + BM25 + graph signals).
- Provide grounded Q&A with citations, traces, and unsupported-answer safeguards.
- Ship a reproducible local workflow with CI-quality checks.

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

Primary package: `src/enterprise_okf_ai/`

- `ingestion`: parsers + normalization
- `okf`: deterministic bundle generation
- `validators`: strict bundle linting
- `graph`: graph construction and exports
- `retrieval`: hybrid routing + retrieval metrics
- `agent`: tool orchestration + agent evaluation
- `api`: FastAPI runtime
- `ui`: Streamlit app

## Quick Start (5 minutes)

```bash
uv sync --extra dev --frozen
UV_CACHE_DIR=.uv-cache make check
UV_CACHE_DIR=.uv-cache make run-e2e
```

Expected strict E2E outcome summary (from local run):
- `validation_errors = 0`
- `validation_warnings = 0`
- API checks (`/health`, `/retrieval/search`, `/agent/ask`, `/agent/evaluate`) all `200`

Run artifact:
- [`artifacts/e2e_real_run/e2e_summary.json`](artifacts/e2e_real_run/e2e_summary.json)

## Setup and Installation

### Prerequisites

- Python 3.11+
- `uv`

### Install

```bash
uv sync --extra dev --frozen
cp .env.example .env
```

Core environment defaults are defined in `.env.example` and loaded by `enterprise_okf_ai.core.settings.Settings`.

## Usage

### Full pipeline workflow

```bash
# Build OKF bundle
uv run enterprise-okf-ai build-okf examples/enterprise_docs artifacts/local_okf_bundle

# Validate bundle
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
- [`HANDBOOK.md`](HANDBOOK.md)
- [`HANDBOOK.pdf`](HANDBOOK.pdf)

## Experiments / Workflow Evidence

Verified command path in this repository:
- `make check`
- `make run-e2e`

Current run highlights (`artifacts/e2e_real_run/e2e_summary.json`):
- graph: `9` nodes / `17` edges
- indexing: `9` files scanned / `11` chunks indexed
- retrieval: results returned (`result_count = 8`)
- agent evaluation summary:
  - `total_cases = 4`
  - `avg_concept_recall = 1.0`
  - `avg_answer_support = 0.5`
  - `abstain_accuracy = 0.5`

## Outputs / Results

Primary generated outputs:
- OKF bundle: `artifacts/e2e_real_run/okf_bundle/`
- graph exports: `artifacts/e2e_real_run/graph/`
- vector DB assets: `artifacts/e2e_real_run/vector_db/`
- summary report: `artifacts/e2e_real_run/e2e_summary.json`

## Limitations

- Local default embeddings use deterministic fallback vectors; production embeddings require provider configuration.
- Abstention calibration is not yet strong (`abstain_accuracy = 0.5` on current benchmark).
- Sample enterprise corpus is realistic but small.
- Legacy compatibility package `src/okfhub/` remains in repo and can add onboarding overhead.

## Future Improvements

- Improve unsupported-answer calibration and add stronger abstention benchmarks.
- Add reranking and richer section-aware retrieval scoring.
- Expand benchmark suite (domain negatives, drift cases, regression thresholds).
- Add containerized deployment profiles and operational observability docs.

## Help & Support

- Troubleshooting guide: [`HANDBOOK.md`](HANDBOOK.md)
- Project issues: <https://github.com/pypi-ahmad/google-okf-implementation/issues>
- Security reports: [`SECURITY.md`](SECURITY.md)

## Maintainers

- Ahmad (`@pypi-ahmad`)

## Contributing and Community

- Contribution guide: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Code of conduct: [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
- Support policy: [`SUPPORT.md`](SUPPORT.md)
- Security policy: [`SECURITY.md`](SECURITY.md)

## References / Sources

### Project-specific references

- Google Cloud OKF overview: <https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing>
- OKF specification (GoogleCloudPlatform): <https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md>
- Architecture notes: [`docs/architecture.md`](docs/architecture.md)
- OKF format notes: [`docs/okf-format.md`](docs/okf-format.md)
- Retrieval notes: [`docs/retrieval.md`](docs/retrieval.md)
- Agent notes: [`docs/agent.md`](docs/agent.md)
- Evaluation notes: [`docs/evaluation.md`](docs/evaluation.md)
- End-to-end evidence artifact: [`artifacts/e2e_real_run/e2e_summary.json`](artifacts/e2e_real_run/e2e_summary.json)

### Official stack documentation

- `uv`: <https://docs.astral.sh/uv/>
- FastAPI: <https://fastapi.tiangolo.com/>
- Typer: <https://typer.tiangolo.com/>
- Pydantic: <https://docs.pydantic.dev/>
- LangChain: <https://python.langchain.com/>
- LangGraph: <https://langchain-ai.github.io/langgraph/>
- ChromaDB: <https://docs.trychroma.com/>
- NetworkX: <https://networkx.org/documentation/stable/>
- PyVis: <https://pyvis.readthedocs.io/>
- PyPDF: <https://pypdf.readthedocs.io/>
- python-docx: <https://python-docx.readthedocs.io/>
- Streamlit: <https://docs.streamlit.io/>
- pytest: <https://docs.pytest.org/>
- GitHub Actions: <https://docs.github.com/actions>

### Documentation quality guidance used for this docs pass

- GitHub README guidance: <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes>
- GitHub docs writing best practices: <https://docs.github.com/en/contributing/writing-for-github-docs/best-practices-for-github-docs>
- Healthy contribution setup: <https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions>
- GitHub Markdown linking: <https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax>
- Diátaxis framework: <https://diataxis.fr/>
- Write the Docs guide: <https://www.writethedocs.org/guide/>
- Microsoft style quick start: <https://learn.microsoft.com/en-us/contribute/content/style-quick-start>
- Microsoft headings/scannability: <https://learn.microsoft.com/en-us/style-guide/scannable-content/headings>

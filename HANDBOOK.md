# enterprise-okf-ai Handbook

Zero-to-mastery manual for understanding, running, validating, and releasing this repository.

## 1. Project Purpose

`enterprise-okf-ai` is an enterprise knowledge engineering system that standardizes heterogeneous documentation into an OKF-style bundle and serves grounded retrieval + agentic Q&A.

What this project solves:
- fragmented organizational knowledge
- weak traceability in raw RAG systems
- poor dependency/ownership reasoning without graph context

Primary business outcome:
- portable, versioned enterprise knowledge that both humans and AI systems can consume.

## 2. Glossary and Definitions

- OKF-style bundle: Directory of markdown concept files with YAML frontmatter metadata and links.
- Frontmatter: YAML metadata block at the top of each concept markdown page.
- Concept: A typed knowledge object (`api`, `dataset`, `metric`, `playbook`, `table`, `glossary`).
- Hybrid retrieval: Ranking strategy combining vector, lexical, graph, and structured signals.
- Graph traversal retrieval: Expands context using knowledge graph neighbors of retrieved concepts.
- Grounded answer: Agent answer backed by retrieved evidence and citations.
- Abstention: Agent behavior to refuse unsupported answers instead of hallucinating.
- Chroma manifest: Local index state file used for idempotent vector updates.

## 3. Prerequisites

- OS: Linux/macOS/Windows (Linux used in this repository run evidence)
- Python: 3.11+
- Package manager: `uv`
- Optional: `gh` (GitHub CLI) for repository publish and release automation

## 4. Environment Setup

### 4.1 Install dependencies

```bash
uv sync --extra dev --frozen
```

### 4.2 Environment variables

Copy and edit:

```bash
cp .env.example .env
```

Default key settings from `.env.example`:
- `PROJECT_NAME=enterprise-okf-ai`
- `OKF_DIR=okf_bundle`
- `VECTOR_DIR=vector_db/chroma`
- `GRAPH_DIR=knowledge_graph`
- `LLM_PROVIDER=ollama`
- `OPENAI_API_KEY=` (optional, only if OpenAI embeddings are used)

### 4.3 Config files

- `configs/app.yaml`: base local runtime defaults
- `configs/pipeline.example.yaml`: sample pipeline profile for artifact-oriented runs

## 5. Dependency Explanations

Main runtime dependencies from `pyproject.toml` and why they exist:

- `fastapi`, `uvicorn`: API service runtime
- `typer`: CLI interface
- `pydantic`, `pydantic-settings`: typed contracts and env config
- `chromadb`: local vector store
- `rank-bm25`: lexical retrieval layer
- `networkx`, `pyvis`: graph modeling and graph visualization
- `pypdf`, `python-docx`, `beautifulsoup4`, `pandas`: heterogeneous document ingestion
- `langchain`, `langgraph`: orchestration surface alignment for AI workflows
- `streamlit`: lightweight local UI
- `loguru`, `orjson`, `pyyaml`: runtime logging and serialization

Quality and release tooling:
- `ruff`, `black`, `mypy`, `pytest`, `pre-commit`

## 6. Repository Structure

High-level map:

```text
.
├── src/enterprise_okf_ai/      # canonical package
├── src/ingest/                 # parser implementation
├── src/rag/                    # retrieval internals
├── src/vector_db/              # vector index internals
├── src/graph/                  # graph builder internals
├── src/validators/             # strict bundle validator internals
├── docs/                       # architecture/format/retrieval/agent/eval docs
├── scripts/                    # notebook and e2e execution helpers
├── examples/                   # sample enterprise source docs + benchmarks
├── notebooks/                  # tutorial notebook
├── tests/                      # unit and integration coverage
└── artifacts/                  # local run outputs (gitignored)
```

Note: `src/okfhub/` exists as a compatibility layer. New implementation focus is `src/enterprise_okf_ai/`.

## 7. Code Walkthrough

### 7.1 Ingestion and normalization

- Entry: `enterprise_okf_ai.ingestion.IngestionService`
- Parser: `ingest.parser.DocumentParser`
- Supported types: `PDF`, `DOCX`, `Markdown`, `CSV`, `HTML`
- Output: `ParsedDocument` objects with metadata, headings, tables, sections, chunks, and provenance.

### 7.2 OKF bundle generation

- Entry: `enterprise_okf_ai.okf.OKFBundleGenerator`
- Responsibilities:
  - infer concept type
  - deterministic slug/id generation
  - deduplication
  - relationship resolution
  - markdown + YAML file writing

Required frontmatter keys:
- `id`, `type`, `title`, `description`, `tags`, `resource`, `sources`, `relationships`, `timestamp`

### 7.3 Validation

- Entry: `enterprise_okf_ai.validators.BundleValidator`
- Core checks (`validators.okf_validator.OKFValidator`):
  - invalid/missing YAML frontmatter
  - missing mandatory fields
  - broken internal links
  - duplicate concepts
  - orphan documents
  - circular references

### 7.4 Knowledge graph

- Entry: `enterprise_okf_ai.graph.GraphService`
- Backend: `graph.builder.KnowledgeGraphBuilder`
- Exports:
  - JSON (`graph.json`)
  - GraphML (`graph.graphml`)
  - interactive HTML (`graph.html`)

### 7.5 Embedding and vector indexing

- Entry: `vector_db.indexer.OKFVectorIndexer`
- Store wrapper: `ChromaVectorStore`
- Behavior:
  - idempotent indexing by file checksum + manifest
  - chunk metadata mapped to frontmatter context

### 7.6 Retrieval

- Entry: `enterprise_okf_ai.retrieval.RetrievalService`
- Core: `rag.retriever.HybridSearchRouter`
- Routes:
  - `auto`
  - `vector`
  - `keyword`
  - `graph`
  - `hybrid`

Each hit returns score and explanation traces.

### 7.7 Agent orchestration

- Entry: `enterprise_okf_ai.agent.AgentOrchestrator`
- Core: `agent.assistant.EnterpriseAssistant`
- Tools used by agent:
  - `search_okf_documents`
  - `search_vector_db`
  - `query_knowledge_graph`
  - `read_okf_file`
  - `summarize_evidence`

Guardrails include evidence thresholds and unsupported-answer handling.

### 7.8 API and UI

- FastAPI app: `enterprise_okf_ai.api.create_app`
- Streamlit app: `src/enterprise_okf_ai/ui/streamlit_app.py`
- CLI entrypoint: `enterprise_okf_ai.cli.main`

## 8. Training / Inference / Pipeline Flow

This repository does **not** train ML models. It performs retrieval and agent inference over structured knowledge artifacts.

Pipeline flow:
1. Ingest source docs.
2. Build OKF bundle.
3. Validate bundle.
4. Build graph.
5. Index vectors.
6. Retrieve evidence.
7. Generate grounded answer with citations.
8. Evaluate retrieval and agent behavior.

## 9. Commands Used (Real)

Commands executed in this repository during verification:

```bash
UV_CACHE_DIR=.uv-cache make check
UV_CACHE_DIR=.uv-cache make run-e2e
```

Observed outputs (latest run):
- lint/typecheck/tests/notebook validation passed
- `45 passed, 1 warning` in pytest
- notebook validator passed with `21` cells (`12` markdown, `9` code)
- strict E2E summary indicates:
  - `validation_errors = 0`
  - `validation_warnings = 0`
  - `graph_nodes = 9`
  - `graph_edges = 17`
  - API statuses all `200`

Source of truth artifact:
- `artifacts/e2e_real_run/e2e_summary.json`

## 10. Configuration Explanation

### 10.1 Runtime settings class

`enterprise_okf_ai.core.settings.Settings` loads `.env` values and resolves relative paths against project root.

Important fields:
- `okf_dir`
- `vector_dir`
- `graph_dir`
- `llm_provider`
- `llm_base_url`
- `llm_chat_model`
- `llm_embed_model`

### 10.2 Config file usage pattern

- `configs/app.yaml` is a standard environment profile.
- `configs/pipeline.example.yaml` documents an end-to-end run profile (source docs, artifact paths, retrieval and agent defaults).

## 11. Validation, Evaluation, and Metrics

### 11.1 Validation metrics

From latest strict run:
- bundle validation passed
- zero errors, zero warnings
- zero cycles and orphans

### 11.2 Retrieval and graph metrics

From latest strict run:
- graph nodes: `9`
- graph edges: `17`
- indexed chunks: `11`
- retrieval result count in summary query: `8`

### 11.3 Agent evaluation metrics

From latest strict run (`agent_evaluation.summary`):
- `total_cases = 4`
- `avg_concept_recall = 1.0`
- `avg_answer_support = 0.5`
- `supported_rate = 0.75`
- `abstain_accuracy = 0.5`

Interpretation:
- Concept coverage is strong for this benchmark set.
- Abstention reliability still needs improvement.

## 12. Outputs and Interpretation

Primary output directories (gitignored):
- `artifacts/e2e_real_run/okf_bundle/`
- `artifacts/e2e_real_run/graph/`
- `artifacts/e2e_real_run/vector_db/`
- `artifacts/e2e_real_run/e2e_summary.json`

What to inspect first:
1. `e2e_summary.json` for pass/fail and metrics
2. `graph/graph.html` for visual relationship checks
3. `okf_bundle/*.md` to validate readability and metadata quality

## 13. Debugging and Troubleshooting

### 13.1 CLI command not found (`enterprise-okf-ai`)

Use module execution if scripts are not installed in shell path:

```bash
PYTHONPATH=src uv run --no-sync python -m enterprise_okf_ai.cli.main --help
```

### 13.2 Git repository appears invalid

If `git` reports not a repository despite `.git` directory presence, initialize a real git repo:

```bash
git init
git add .
git commit -m "chore: initialize repository"
```

### 13.3 GitHub auth invalid

If `gh auth status` reports invalid token:

```bash
gh auth login -h github.com
```

### 13.4 Chroma warning in tests

A deprecation warning from `chromadb` may appear (`asyncio.iscoroutinefunction`). It is non-fatal in current runs.

## 14. Deployment and Execution Notes

Local service startup:

```bash
make run-api
make run-ui
```

FastAPI endpoints to verify:
- `POST /retrieval/search`
- `POST /agent/ask`
- `POST /agent/evaluate`

CI workflows:
- `.github/workflows/ci.yml`
- `.github/workflows/notebook-validation.yml`

## 15. Best Practices and Lessons Learned

- Keep bundle generation deterministic to preserve clean git diffs.
- Treat validation as a release gate, not optional diagnostics.
- Preserve retrieval traces and citations for auditability.
- Track abstention metrics explicitly to reduce hallucination risk.
- Use strict E2E runs before release tags.

## 16. Release Workflow (Recommended)

1. Run:

```bash
make check
make run-e2e
```

2. Prepare release notes (`RELEASE_NOTES.md`) from real metrics.
3. Ensure `gh auth status` is valid.
4. Create/push repository and tag.
5. Create GitHub release.

## 17. Official References and Sources

Project references:
- Google Cloud OKF article:
  - https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing
- OKF specification:
  - https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md

Official documentation for stack used in this repository:
- uv: https://docs.astral.sh/uv/
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

Repository evidence files:
- `artifacts/e2e_real_run/e2e_summary.json`
- `pyproject.toml`
- `Makefile`
- `.github/workflows/ci.yml`
- `.github/workflows/notebook-validation.yml`

# From Fragmented Documents to an Enterprise Knowledge Brain: Building an OKF + Graph + Hybrid RAG + Agent System

## Executive Summary

Most "enterprise RAG" demos stop at uploading PDFs and asking questions. That pattern breaks quickly in real organizations because enterprise knowledge is not only unstructured text; it is also relationships, ownership, formulas, and operational dependencies spread across APIs, runbooks, schemas, incidents, and glossary terms.

This project, `enterprise-okf-ai`, implements a full knowledge lifecycle:

1. ingest heterogeneous documents,
2. normalize and compile them into deterministic OKF-style markdown concepts,
3. validate bundle integrity,
4. build a directed knowledge graph,
5. index concepts for semantic retrieval,
6. run hybrid retrieval (vector + lexical + graph signals),
7. orchestrate a tool-using agent with explicit grounding and abstention behavior.

The system is intentionally production-oriented: typed modules, deterministic outputs, diagnostics, report artifacts, CLI/API/UI surfaces, and benchmark hooks.

This article explains how the architecture works, what was learned from a real run, and why this approach is stronger than raw-document RAG for enterprise settings.

## Why Raw-Document RAG Underperforms in Enterprise Settings

Raw-document RAG has a structural blind spot: it retrieves chunks, not concepts. Enterprise questions often require traversing explicit relationships across concept types.

Examples:

- "Which API updates customer orders, and which dataset does it depend on?"
- "How is Monthly Active Users calculated?"
- "Show me the runbook for payment failures."
- "Which team owns this API and what dashboards depend on it?"

These are not only semantic similarity problems. They are relation, lineage, and governance problems.

Typical failure modes of naive RAG:

- It retrieves semantically similar but structurally irrelevant chunks.
- It misses dependencies that are one or two hops away.
- It cannot distinguish canonical definitions from duplicate mentions.
- It answers unsupported questions with confident hallucinations.

The core design choice in this repo is to treat knowledge as **compiled artifacts** first, and conversational reasoning second.

## The OKF Shift: Knowledge as Portable, Versioned Objects

Google’s Open Knowledge Format (OKF) motivation is straightforward: represent organizational knowledge as markdown files with structured metadata so it is both human-readable and machine-consumable.

In this project, each concept becomes a markdown page with strict frontmatter keys:

- `id`
- `type`
- `title`
- `description`
- `tags`
- `resource`
- `sources`
- `relationships`
- `timestamp`

Canonical bundle layout:

```text
okf_bundle/
  apis/
  datasets/
  metrics/
  playbooks/
  tables/
  glossary/
  README.md
  bundle_manifest.yaml
```

This gives three concrete engineering benefits:

1. deterministic diffs in Git for knowledge changes,
2. typed retrieval surfaces (API vs metric vs runbook),
3. explicit relationship edges for graph and validator logic.

## System Architecture: Deterministic Core + Probabilistic Edge

At a high level:

```text
Raw Documents
  -> Ingestion + Normalization
  -> OKF Bundle Generation
  -> Validation + Health Reporting
  -> Knowledge Graph Build
  -> Embedding + Vector Index
  -> Hybrid Retrieval Router
  -> Tool-Calling Agent
  -> Evaluation Harness
  -> CLI / API / Streamlit
```

Canonical package path is `src/enterprise_okf_ai/`, with a legacy compatibility surface in `src/okfhub/`.

The architecture intentionally separates:

- **deterministic systems** (ingestion, compilation, validation, graph construction),
- **probabilistic systems** (retrieval ranking and final answer synthesis).

That separation is what makes debugging and release quality practical.

## Step 1: Ingestion and Normalization

The ingestion layer supports:

- Markdown / text
- PDF (`pypdf`)
- DOCX (`python-docx`)
- CSV
- HTML (`BeautifulSoup`)

The parser normalizes each source into a common object with:

- content,
- document-level metadata (author, creation date where available),
- headings,
- tables,
- sections,
- deterministic chunks,
- provenance and parser errors.

Important engineering detail: chunking follows section boundaries first, then applies character windows with overlap. This is better than blind fixed-size chunking because it preserves local semantic structure.

Relevant implementation surfaces:

- `ingest.parser.DocumentParser`
- `enterprise_okf_ai.ingestion.IngestionService`
- CLI command: `enterprise-okf-ai ingest <path>`

## Step 2: OKF Compiler and Canonicalization

The OKF compiler (`OKFBundleGenerator`) converts normalized documents into canonical concept pages.

Key behaviors implemented:

- concept type inference using path-first and content fallback heuristics,
- deterministic slug generation,
- per-type folder routing (`apis`, `datasets`, `metrics`, `playbooks`, `tables`, `glossary`),
- deduplication into canonical concepts,
- relationship extraction and resolution,
- YAML serialization and validation before write.

This is where the system shifts from "documents" to "knowledge objects."

It also enables meaningful diffing because concept IDs and paths are stable across runs.

## Step 3: Validation as a Hard Quality Gate

Before graphing or retrieval, the bundle passes strict validation (`OKFValidator`).

Checks include:

- invalid YAML frontmatter,
- missing mandatory fields,
- broken markdown/relationship links,
- duplicate concept definitions,
- orphan documents,
- circular references.

Why this matters: retrieval and agents amplify data quality issues. If links are broken or concepts are duplicated, confidence scores become meaningless and citations degrade.

In other words, validation is not documentation hygiene; it is inference safety infrastructure.

## Step 4: Knowledge Graph Construction

The graph builder (`KnowledgeGraphBuilder`) creates a `networkx.DiGraph` from OKF documents.

Nodes contain concept metadata:

- `id`
- `title`
- `type`
- `path`
- `description`
- `tags`

Edges are typed by relation source:

- `markdown_link`
- `frontmatter_relationship`
- `dependency`

Exports:

- JSON node-link format,
- GraphML,
- interactive HTML via PyVis.

This graph unlocks relation-heavy retrieval. If an API is retrieved, neighboring datasets/metrics/tables can be pulled in one or two hops instead of hoping semantic search lands on all required context.

## Step 5: Embeddings and Idempotent Vector Indexing

The vector indexer (`OKFVectorIndexer`) chunks each concept and writes embeddings + metadata to local Chroma.

Notable production behavior:

- idempotent indexing via per-file checksums and a persisted manifest,
- changed files are re-indexed, unchanged files are skipped,
- deleted files trigger chunk deletions from the vector store,
- chunk metadata preserves OKF attributes (`type`, `title`, `resource`, `tags`, `timestamp`, `checksum`).

Embedding providers:

- `sentence-transformers` (default path),
- OpenAI embeddings,
- deterministic local fallback embedding utility for local reproducibility workflows.

## Step 6: Hybrid Retrieval Router (Vector + BM25 + Graph Signals)

The retrieval layer (`HybridSearchRouter`) supports five routes:

- `auto`
- `vector`
- `keyword`
- `graph`
- `hybrid`

Internally, retrieval combines:

- semantic vector similarity,
- BM25 lexical scoring,
- graph proximity scoring,
- structured type-aware boosts.

Each result includes:

- concept ID and type,
- final score,
- score breakdown (`semantic`, `keyword`, `graph`, `structured`, `final`),
- explanation traces.

This is essential for AI engineering workflows because you can inspect "why this result ranked here" instead of tuning a black box.

## Step 7: Agent Orchestration with Tool Use and Guardrails

The assistant (`EnterpriseAssistant`) uses explicit tools:

1. `search_okf_documents`
2. `search_vector_db`
3. `query_knowledge_graph`
4. `read_okf_file`
5. `summarize_evidence`

Strategy policy:

- structured relationship questions -> graph-first,
- broad semantic questions -> retrieval-first.

Safety controls:

- minimum top-score threshold,
- evidence-hit checks,
- lexical overlap checks,
- explicit unsupported-answer payloads (`supported`, `unsupported_reason`).

Response payload includes:

- answer,
- citations,
- used concepts,
- tool trace,
- tool calls,
- evidence summary,
- confidence,
- support status and reason.

This makes the agent auditable rather than purely conversational.

## Real End-to-End Run: What Actually Happened

This project includes a strict end-to-end run artifact at:

- `artifacts/e2e_real_run/e2e_summary.json`

Key outcomes from the latest verified run:

- Build:
  - `concept_count = 9`
  - `deduplicated_concepts = 1`
- Validation:
  - `errors = 0`
  - `warnings = 0`
  - `broken_links = 0`
  - `orphans = 0`
  - `cycles = 0`
- Graph:
  - `nodes = 9`
  - `edges = 17`
- Retrieval evaluation:
  - `avg_recall_at_k = 1.0`
  - `avg_mrr = 0.5`
  - `avg_answer_support = 0.8333`
- Agent evaluation:
  - `avg_concept_recall = 1.0`
  - `avg_answer_support = 0.5`
  - `abstain_accuracy = 0.5`
  - `supported_rate = 0.75`
- API probes:
  - `/health = 200`
  - `/retrieval/search = 200`
  - `/agent/ask = 200`
  - `/agent/evaluate = 200`

Interpretation:

- Core pipeline integrity is strong (zero validation issues, stable graph/index/build outputs).
- Retrieval is finding expected concepts reliably on the current benchmark.
- Agent abstention behavior is not yet production-grade and needs calibration/benchmark expansion.

That last point is exactly the kind of honest signal hiring teams value: measurable strength, measurable gap, explicit next action.

## Why This Is AI Engineering, Not Just "ML"

This project demonstrates core AI engineering competencies:

- data contract design (OKF frontmatter and concept taxonomy),
- compiler-style normalization and deterministic outputs,
- retrieval system design with route reasoning and observability,
- safety-oriented agent orchestration with abstention logic,
- evaluation harnesses for retrieval and agent behavior,
- multi-surface delivery (CLI, API, Streamlit),
- CI/release readiness and reproducible local workflows.

Model choice is almost the least interesting part here. System design and reliability are the differentiators.

## Failure Modes and What to Improve Next

1. Abstention quality is weak on the current benchmark (`0.5`).
2. Benchmark set is small and should include harder negatives and drift scenarios.
3. Retrieval could improve ranking of exact metric-definition questions (better lexical/structured reweighting and reranking).
4. Corpus scale is currently realistic but limited; stress testing on larger enterprise corpora is needed.
5. Legacy compatibility package (`src/okfhub/`) should be eventually rationalized to reduce contributor ambiguity.

## Practical Productionization Roadmap

If this were taken from strong prototype to deployment candidate:

1. Replace deterministic local embeddings with production embedding providers in all environments.
2. Add reranker stage and route-specific confidence calibration.
3. Expand eval suite with:
   - unsupported-policy questions,
   - contradictory-source cases,
   - temporal drift checks,
   - ownership/lineage multi-hop queries.
4. Add policy checks for stale `timestamp`, missing owner metadata, and concept lifecycle states.
5. Gate release on explicit threshold policies for retrieval and agent metrics.
6. Add telemetry and incident playbooks for retrieval regressions.

## Reproducibility and Commands

Install + checks:

```bash
uv sync --extra dev --frozen
UV_CACHE_DIR=.uv-cache make check
```

Strict E2E:

```bash
UV_CACHE_DIR=.uv-cache make run-e2e
```

Core CLI flow:

```bash
uv run enterprise-okf-ai build-okf examples/enterprise_docs artifacts/local_okf_bundle
uv run enterprise-okf-ai okf-validate --okf-dir artifacts/local_okf_bundle
uv run enterprise-okf-ai graph-build --okf-dir artifacts/local_okf_bundle
uv run enterprise-okf-ai retrieve-search "Which API updates order status?" --with-trace
uv run enterprise-okf-ai agent-ask "Which API updates order status and what does it depend on?"
```

## Closing

A high-quality enterprise AI system is not a chatbot wrapper. It is a knowledge engineering pipeline with deterministic contracts, validation gates, graph structure, retrieval observability, and measurable safety behavior.

That is the central value of this implementation: it treats enterprise knowledge as a first-class, versioned system that both humans and agents can trust.

## References

### Primary OKF references

- Google Cloud: How the Open Knowledge Format can improve data sharing  
  <https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing>
- OKF specification (GoogleCloudPlatform)  
  <https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md>

### Repository evidence

- Architecture overview: `docs/architecture.md`
- OKF format guide: `docs/okf-format.md`
- Retrieval guide: `docs/retrieval.md`
- Agent guide: `docs/agent.md`
- Evaluation guide: `docs/evaluation.md`
- Real run artifact: `artifacts/e2e_real_run/e2e_summary.json`

### Official stack docs

- uv: <https://docs.astral.sh/uv/>
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

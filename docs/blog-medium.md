# Beyond "Chat with PDFs": Building an Enterprise Knowledge Brain with OKF, Graph Retrieval, and Agentic RAG

> A production-oriented walkthrough of how `enterprise-okf-ai` converts fragmented docs into a validated, graph-aware, agent-consumable knowledge system.

## TL;DR

Most enterprise RAG implementations fail because they index text, not knowledge.  
This project (`enterprise-okf-ai`) implements a full lifecycle:

- ingest heterogeneous enterprise documents,
- compile them into strict OKF-style markdown concepts,
- validate structural integrity,
- build a typed knowledge graph,
- run hybrid retrieval (vector + BM25 + graph),
- orchestrate a tool-calling agent with evidence and abstention controls.

It is less "prompt engineering demo" and more "knowledge systems engineering."

## The Real Problem with Enterprise Knowledge

In real teams, knowledge lives everywhere:

- API docs
- runbooks/playbooks
- data dictionary and SQL schemas
- incident writeups
- Markdown and wiki pages
- CSV extracts
- glossary notes

Raw-document RAG struggles here for structural reasons:

1. It retrieves semantically similar chunks, not canonical concepts.
2. It has weak dependency reasoning across documents.
3. It confuses mentions with definitions.
4. It often answers unsupported questions anyway.

If your query is "Which API updates order status and what dataset does it depend on?", cosine similarity alone is not enough.

## Why OKF as the Core Abstraction

Google’s Open Knowledge Format (OKF) pushes a simple but powerful idea: represent organizational knowledge as markdown with structured YAML frontmatter so it is portable, versioned, and machine-readable.

In this project, each concept page includes:

- `id`
- `type`
- `title`
- `description`
- `tags`
- `resource`
- `sources`
- `relationships`
- `timestamp`

This turns "documents" into "knowledge objects" that can be validated, linked, diffed, and retrieved with stronger guarantees.

## Architecture: Deterministic Core, Probabilistic Edge

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

Design principle: do deterministic work first (contracts, structure, integrity), then apply probabilistic components (ranking and answer synthesis).

## Implementation Walkthrough

### 1) Ingestion and normalization

Supported types:

- Markdown/text
- PDF (`pypdf`)
- DOCX (`python-docx`)
- CSV
- HTML

Each file is normalized into a common object containing:

- content
- metadata (author/date where available)
- headings and sections
- extracted tables
- deterministic chunks
- provenance and parser errors

### 2) OKF bundle generation

Compiler behavior includes:

- type inference (`api`, `dataset`, `metric`, `playbook`, `table`, `glossary`)
- deterministic slug/ID generation
- deduplication into canonical entries
- relationship extraction/resolution
- strict YAML validation before write

### 3) Validation as a release gate

Validator checks:

- invalid YAML frontmatter
- missing required fields
- broken internal links
- duplicate concepts
- orphan pages
- circular references

This is not cosmetic quality. It protects retrieval and agent behavior from upstream data integrity failures.

### 4) Knowledge graph

`networkx.DiGraph` built from frontmatter + markdown links.

Edge types include:

- `markdown_link`
- `frontmatter_relationship`
- `dependency`

Graph exports:

- JSON
- GraphML
- interactive HTML (PyVis)

### 5) Hybrid retrieval

Router supports:

- `auto`
- `vector`
- `keyword`
- `graph`
- `hybrid`

Signals combined:

- semantic vector similarity
- BM25 lexical relevance
- graph proximity
- structured type-aware boosts

Every result returns score breakdown and explanation traces, which makes ranking behavior debuggable.

### 6) Agent orchestration

Tools:

1. `search_okf_documents`
2. `search_vector_db`
3. `query_knowledge_graph`
4. `read_okf_file`
5. `summarize_evidence`

Policy:

- structured dependency questions -> graph-first
- broad conceptual questions -> retrieval-first

Safety:

- evidence thresholds
- top-score thresholds
- overlap checks
- explicit unsupported responses

## Real Run Results (No Mock Data)

From `artifacts/e2e_real_run/e2e_summary.json` (latest local verified run):

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

Interpretation:

- pipeline integrity and retrieval are strong on current benchmark scope,
- abstention quality needs improvement before claiming production-readiness.

## Why This Matters for AI Engineering

This project demonstrates skills employers actually care about in GenAI systems:

- knowledge modeling and data contracts
- deterministic compilation pipelines
- retrieval observability and route control
- graph-aware context expansion
- safety-oriented agent behavior
- benchmark-driven iteration
- multi-interface delivery (CLI/API/UI)

It is an engineering system, not a prompt wrapper.

## What I Would Improve Next

1. Improve abstention calibration and unsupported-answer handling.
2. Expand benchmark coverage with hard negatives and drift cases.
3. Add reranking for exact metric-definition questions.
4. Strengthen governance metadata (`owner`, freshness policy, lifecycle state).
5. Add regression threshold gating in CI for retrieval and agent metrics.

## Reproduce Locally

```bash
uv sync --extra dev --frozen
UV_CACHE_DIR=.uv-cache make check
UV_CACHE_DIR=.uv-cache make run-e2e
```

## References

- Google Cloud OKF overview: <https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing>
- OKF spec: <https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md>
- Repo deep dive: `docs/blog.md`
- Architecture: `docs/architecture.md`
- Retrieval: `docs/retrieval.md`
- Agent: `docs/agent.md`
- Evaluation: `docs/evaluation.md`
- Real run artifact: `artifacts/e2e_real_run/e2e_summary.json`


# Beyond Chatbots: Engineering a Real Enterprise Knowledge System with OKF, Graphs, and Agentic Retrieval

## Why I Built This

Most enterprise AI projects start with the same promise: "Ask anything about your documents."

Most of them hit the same wall:

- answers sound plausible but miss dependencies,
- ownership questions return generic text,
- metric definitions are inconsistent,
- unsupported questions still get confident responses.

The root issue is architectural. We often treat enterprise knowledge as a bag of text chunks and expect embeddings to do everything.

I wanted a different approach: model enterprise knowledge as versioned, structured artifacts first, then layer retrieval and agentic reasoning on top.

That is what `enterprise-okf-ai` implements.

## The Problem Raw RAG Doesn’t Solve

Enterprise knowledge is not just prose.

It includes:

- API contracts and endpoint behavior
- datasets and tables
- metric definitions and formulas
- runbooks and incident procedures
- glossary terms and business acronyms
- links and dependencies between all of the above

A typical raw-document RAG pipeline excels at semantic resemblance, but enterprise queries are often relational:

- "Which API updates order status and what dataset does it depend on?"
- "How is Monthly Active Users calculated?"
- "Show the runbook for payment failures."
- "What upstream concepts affect this table?"

These require structure and traversal, not only similarity scoring.

## The Core Design Choice: Compile Knowledge First

Instead of going directly from raw docs to embeddings, this project introduces a deterministic compilation layer using OKF-style markdown.

Each concept is written as a markdown file with strict YAML frontmatter:

- `id`
- `type`
- `title`
- `description`
- `tags`
- `resource`
- `sources`
- `relationships`
- `timestamp`

Directory layout is stable:

```text
okf_bundle/
  apis/
  datasets/
  metrics/
  playbooks/
  tables/
  glossary/
```

This gives versionable, portable, inspectable knowledge objects.  
Git diffs become meaningful. Validation becomes enforceable. Graph construction becomes reliable.

## Full Architecture

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

The key principle is separation:

- deterministic stages produce reliable knowledge artifacts,
- probabilistic stages perform ranking and answer synthesis over validated artifacts.

That separation dramatically improves debuggability.

## Ingestion: Normalize Heterogeneous Inputs into One Internal Contract

Supported formats:

- Markdown/text
- PDF
- DOCX
- CSV
- HTML

The parser normalizes each source into a unified object that includes:

- raw text,
- headings and section structure,
- extracted tables,
- document-level metadata (when available),
- deterministic chunks,
- provenance and parse errors.

This is subtle but important: you can carry semantic structure from day one instead of flattening everything into untyped text blobs.

## Compiler: Turning Documents into Canonical Concepts

The OKF generator infers concept types, produces deterministic slugs/IDs, deduplicates repeated definitions, and writes strict markdown pages.

Why this matters:

- canonical IDs prevent concept drift,
- deterministic output makes CI and reviews meaningful,
- relationship fields become machine-usable for graph and retrieval.

It is effectively a domain-specific compiler for enterprise knowledge.

## Validation: The Most Underrated Layer in AI Pipelines

The validator checks:

- YAML parseability,
- mandatory metadata,
- broken internal links,
- duplicate canonical concepts,
- orphan pages,
- cycles in references.

In many AI systems, validation is treated as optional hygiene. Here, it is a hard gate.

If this layer is weak, every downstream metric is inflated and every agent answer is less trustworthy.

## Graph: Recovering the Structure RAG Misses

A directed graph (`networkx`) is built from concept relationships and links.

Node data includes concept identity and metadata.  
Edges preserve relation types (`markdown_link`, `frontmatter_relationship`, `dependency`).

Exports are generated in:

- JSON,
- GraphML,
- interactive HTML.

This enables relation-aware retrieval. When an API is retrieved, adjacent dataset/metric/table nodes can be traversed automatically.

## Retrieval: A Router, Not a Single Strategy

The retrieval layer supports:

- vector search,
- BM25 keyword search,
- graph retrieval,
- weighted hybrid,
- auto route selection.

Each result contains:

- ranked score,
- signal breakdown,
- explanation trace.

This is a practical engineering decision. You can inspect route and scoring behavior during failures instead of guessing what happened.

## Agent: Tool-Using, Grounded, and Allowed to Abstain

The agent orchestrates five tools:

1. local OKF lexical search,
2. vector/hybrid search,
3. graph traversal,
4. OKF page read,
5. evidence summarization.

Policy:

- structured dependency questions -> graph-first,
- broad semantic questions -> retrieval-first.

Safeguards:

- minimum evidence and score thresholds,
- overlap checks,
- explicit support/unsupported state,
- citation payloads and tool traces.

That gives you an auditable response contract instead of opaque free-form chat output.

## What the Real Run Shows

The repository includes strict end-to-end run output in:

- `artifacts/e2e_real_run/e2e_summary.json`

Latest verified metrics:

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

This tells a clear story:

- the deterministic core and retrieval pipeline are already solid on the current benchmark,
- agent abstention still needs stronger calibration and evaluation depth.

That is exactly the type of transparent engineering narrative I trust in AI projects.

## Why This Is a Strong AI Engineering Project

It demonstrates:

- knowledge schema and contract design,
- deterministic compilation and validation,
- graph + retrieval system integration,
- tool-using agent orchestration,
- observability via traces and diagnostics,
- benchmark-driven iteration and honest limitations.

In other words, this is not only "can I call an LLM API?"  
It is "can I design, validate, and operate an enterprise knowledge system?"

## What I’d Change Next for Production

1. Improve unsupported-answer calibration and scoring thresholds.
2. Expand benchmark suites with:
   - hard negatives,
   - contradiction cases,
   - temporal drift questions,
   - multi-hop ownership/lineage tasks.
3. Add reranking for exact metric/schema questions.
4. Add governance checks:
   - owner metadata,
   - freshness SLAs,
   - concept lifecycle state.
5. Introduce explicit release thresholds for retrieval/agent quality in CI.

## How to Reproduce

```bash
uv sync --extra dev --frozen
UV_CACHE_DIR=.uv-cache make check
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

## Closing Thought

Enterprise AI quality is less about one perfect prompt and more about systems discipline:

- structure before inference,
- validation before retrieval,
- traces before confidence,
- evidence before answers.

If we build with that order of operations, enterprise agents become more than demos. They become reliable infrastructure.

## References

- Google Cloud OKF overview: <https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing>
- OKF specification: <https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md>
- Repo deep dive: `docs/blog.md`
- Architecture: `docs/architecture.md`
- OKF format guide: `docs/okf-format.md`
- Retrieval guide: `docs/retrieval.md`
- Agent guide: `docs/agent.md`
- Evaluation guide: `docs/evaluation.md`
- Verified run artifact: `artifacts/e2e_real_run/e2e_summary.json`


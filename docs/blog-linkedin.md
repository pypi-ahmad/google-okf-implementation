# Building an Enterprise Knowledge Brain (Not Just "Chat with PDFs")

I shipped a production-oriented project called `enterprise-okf-ai` to solve a problem most enterprise RAG demos ignore:

Enterprise knowledge is fragmented across APIs, runbooks, schemas, incidents, glossary pages, and markdown docs.  
Raw-document RAG usually fails on relationship-heavy questions.

## What I built

An end-to-end knowledge system:

```text
Raw Docs -> Ingestion -> OKF Bundle -> Validation -> Knowledge Graph
        -> Embeddings + Vector Index -> Hybrid Retrieval -> Agentic Q&A
```

## Why this design

I used OKF-style markdown + YAML frontmatter as the canonical format, then added strict validation and graph structure before retrieval/agent layers.

That gave me:

- deterministic, versionable knowledge artifacts,
- explicit relationships between APIs/datasets/metrics/runbooks,
- cleaner retrieval and safer agent answers.

## Key implementation highlights

- Ingestion for `PDF`, `DOCX`, `Markdown`, `CSV`, `HTML`
- Deterministic OKF compiler with concept typing + deduplication
- Validator for YAML integrity, broken links, duplicates, orphans, cycles
- `networkx` knowledge graph with JSON/GraphML/HTML exports
- Hybrid retrieval router (`vector`, `keyword`, `graph`, `hybrid`, `auto`)
- Tool-calling agent with citations, tool traces, and unsupported-answer safeguards

## Real results from latest strict run (July 3, 2026)

From `artifacts/e2e_real_run/e2e_summary.json`:

- Validation: `0` errors, `0` warnings
- Graph: `9` nodes, `17` edges
- Retrieval eval:
  - `avg_recall@k = 1.0`
  - `avg_mrr = 0.5`
  - `avg_answer_support = 0.8333`
- Agent eval:
  - `avg_concept_recall = 1.0`
  - `avg_answer_support = 0.5`
  - `abstain_accuracy = 0.5`

So the core pipeline is strong, but abstention still needs calibration before production claims.

## What this project demonstrates

For me, this is AI engineering more than ML:

- knowledge contracts and compiler thinking
- graph + retrieval systems design
- observability and explanation traces
- safety behavior (support vs abstain)
- evaluation-first iteration

## What I’d improve next

1. Better unsupported-answer calibration
2. Larger benchmark suite with hard negatives + drift
3. Reranking for exact schema/metric definition questions
4. Governance metadata policies (`owner`, freshness, lifecycle state)

If you’re building enterprise GenAI, I’d strongly recommend treating knowledge as a first-class versioned system before building the chat layer.

Project:

- Repo: <https://github.com/pypi-ahmad/google-okf-implementation>
- Deep technical article: `docs/blog.md`
- OKF references:
  - <https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing>
  - <https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md>


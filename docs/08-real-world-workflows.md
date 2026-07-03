# 08 — Real-World Workflows: The Full Pipeline

Everything so far was about the OKF *format*. This page runs the actual
`enterprise-okf-ai` *pipeline* end to end, on the sample enterprise
documents shipped in this repo, using only CLI commands — every command
and output below was run against this exact repository while writing
this page.

## The six-stage pipeline

```text
Raw Documents (examples/enterprise_docs/)
  -> 1. build-okf     (generate an OKF bundle)
  -> 2. okf-validate  (check it against this repo's strict profile)
  -> 3. graph-build   (build a knowledge graph from concept links)
  -> 4. index-build   (embed + persist a vector index)
  -> 5. retrieve-search (query the bundle)
  -> 6. agent-ask     (grounded Q&A over the bundle)
```

Full background on *why* it's shaped this way is in
[`docs/architecture.md`](architecture.md); this page is the hands-on
walkthrough.

> **New CLI command in this release: `index-build`.** Earlier versions
> of this project's docs told you to run `build-okf` then jump straight
> to `retrieve-search` — that sequence actually crashes
> (`FileNotFoundError: OKF directory not found`), because nothing ever
> built the vector index `retrieve-search`/`agent-ask` depend on. This
> page's sequence includes the fix: run `index-build` between
> `graph-build` and `retrieve-search`.

## Step 1 — build an OKF bundle from raw documents

```bash
uv run enterprise-okf-ai build-okf examples/enterprise_docs okf_bundle
```

`build-okf` treats `okf_bundle/` as a build artifact directory and
overwrites it on each run (it deletes any existing `okf_bundle/` first).
This avoids stale files from older runs and keeps output deterministic.

`examples/enterprise_docs/` contains realistic, messy input: two
slightly different Markdown files describing the same API (testing
deduplication), a CSV schema, an HTML incident report, and a glossary
table. **Expected output** (concept count and file list, abbreviated):

```json
{
  "concept_count": 9,
  "concepts_by_type": {"api": 1, "dataset": 1, "glossary": 3, "metric": 1, "playbook": 2, "table": 1},
  "deduplicated_concepts": 1,
  "files_written": ["okf_bundle/apis/orders-api.md", "... 8 more concept files", "okf_bundle/index.md", "okf_bundle/bundle_manifest.yaml"]
}
```

`deduplicated_concepts: 1` means the generator noticed
`orders_api.md` and `orders_api_duplicate.md` describe the same
concept and merged them — see
[`docs/okf-format.md`](okf-format.md#determinism-and-reproducibility).

The generator writes a bundle-root `index.md` (OKF reserved filename)
and includes an optional `okf_version: \"0.1\"` declaration in its
frontmatter (spec §11).

## Step 2 — validate it

```bash
uv run enterprise-okf-ai okf-validate --okf-dir okf_bundle
```

**Expected output:**

```json
{"passed": true, "issues": [], "stats": {"files_scanned": 9, "documents_parsed": 9, "errors": 0, "warnings": 0, "edges": 34, "cycles": 0, "orphans": 0, "duplicate_concepts": 0, "broken_links": 0}}
```

If you see errors here, stop and fix them before continuing — a graph
or vector index built on top of an invalid bundle inherits its
problems. Full error-code reference: [07 — Conformance & Validation](07-conformance-and-validation.md).

## Step 3 — build the knowledge graph

```bash
uv run enterprise-okf-ai graph-build --okf-dir okf_bundle
```

**Expected output:**

```text
{'nodes': 9, 'edges': 17, 'json_path': '.../knowledge_graph/graph.json', 'html_path': '.../knowledge_graph/graph.html', 'graphml_path': '.../knowledge_graph/graph.graphml'}
```

Open `knowledge_graph/graph.html` in a browser — it's a self-contained
PyVis visualization of the 9 concepts and how they reference each
other. `nodes`/`edges` here can differ from the validator's own
`edges: 34` count: the validator counts every markdown link and
`relationships` entry as a candidate edge before dedup, the graph
builder consolidates them into a simple graph.

## Step 4 — build the vector index

```bash
uv run enterprise-okf-ai index-build --okf-dir okf_bundle
```

**Expected output:**

```json
{"vector_dir": ".../vector_db/chroma", "files_scanned": 9, "files_changed": 9, "files_removed": 0, "chunks_indexed": 10, "chunks_deleted": 0}
```

This step is **idempotent** — re-run it any time the bundle changes,
and it only re-embeds files whose checksum changed
(`files_changed`/`chunks_indexed` will be `0` on an unchanged bundle).
It uses the same `deterministic_embedding` fallback described in
[02 — Prerequisites](02-prerequisites.md) — no API key, no local model
download.

## Step 5 — search the bundle

```bash
uv run enterprise-okf-ai retrieve-search "Which API updates order status?" --with-trace
```

**Expected output (top result):** the router selects `hybrid` mode and
ranks `apis/orders-api` first with a score breakdown showing exactly
which signal — semantic, keyword, or structured — contributed:

```json
{"route": "hybrid", "router_trace": ["auto route selected hybrid ensemble due to mixed query intent", "weights=semantic:0.51,keyword:0.40,graph:0.00,structured:0.10"],
 "results": [{"concept_id": "apis/orders-api", "title": "Orders API", "score": 0.6806, "score_breakdown": {"semantic": 0.369, "keyword": 1.0, "structured": 1.0}}]}
```

Full explanation of routes and scoring: [`docs/retrieval.md`](retrieval.md).

## Step 6 — ask the agent a question

```bash
uv run enterprise-okf-ai agent-ask "Which API updates order status and what does it depend on?"
```

**Expected output (trimmed):** the agent picks `graph_first` strategy
(because "depend on" is a structured/dependency term — see
[`docs/agent.md`](agent.md#strategy-selection)), calls five tools in
sequence, and returns a grounded answer citing six concept files:

```json
{"strategy": "graph_first", "supported": true, "confidence": 0.7083,
 "used_concepts": ["apis/orders-api", "datasets/customer-profile-dataset", "metrics/monthly-active-users", "playbooks/incident-payment-outage", "playbooks/payment-failure-playbook", "tables/orders-fact"],
 "answer": "Question: Which API updates order status and what does it depend on?\n\nGrounded evidence summary:\n- [apis/orders-api] description: '`PATCH /v2/orders/{order_id}` updates order status...' \n...\n\nGrounding: The answer is based only on retrieved OKF evidence."}
```

Remember from [02 — Prerequisites](02-prerequisites.md): this answer
was composed by rule-based evidence summarization (`llm=None`), not a
hosted LLM — that's why it reads as structured bullet points quoting
the source files directly rather than free-flowing prose. See
[11 — Next Steps](11-next-steps.md) to wire in a real LLM.

## Re-running after you change the bundle

Whenever you re-run `build-okf` (new source documents, edited files),
re-run steps 2–4 in order — `okf-validate` first, then `graph-build`
and `index-build`. `retrieve-search`/`agent-ask` always read whatever
is currently on disk at `okf_bundle/`, `knowledge_graph/`, and
`vector_db/chroma/` (the defaults from `Settings` — see
[`.env.example`](../.env.example) to point them elsewhere).

## The one-command version

Everything above, plus a FastAPI health/endpoint smoke check, is what
`make run-e2e` runs automatically against `artifacts/e2e_real_run/`
(a separate, isolated output directory, so it won't collide with the
`okf_bundle/` you just built by hand):

```bash
make run-e2e
```

See [`scripts/run_real_e2e.py`](../scripts/run_real_e2e.py) for exactly
what it does — it's the same six stages, called from Python directly
instead of chained CLI commands, plus retrieval/agent evaluation
metrics (covered in [`docs/evaluation.md`](evaluation.md)).

Next: [09 — Troubleshooting](09-troubleshooting.md).

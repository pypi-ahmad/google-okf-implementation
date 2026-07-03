# enterprise-okf-ai

**Learn Google Cloud's Open Knowledge Format (OKF) from zero, then see
it power a real enterprise knowledge pipeline.** This repository is
both a working system — ingestion → OKF bundle → validation →
knowledge graph → hybrid retrieval → grounded AI agent — and a
guided, zero-to-mastery learning path for OKF itself.

## Project Status

`Beta` (`v0.3.0`): production-oriented architecture and validation
gates are in place, the CLI-only golden path is verified end to end,
and the docs are a full beginner-to-practitioner learning path. Agent
abstention calibration and benchmark depth still need improvement (see
[Limitations](#limitations)).

## Who this is for

- **Complete beginners to OKF** — you've never heard of it and want to
  understand it from first principles, independent of this repo.
- **Developers evaluating OKF-shaped knowledge bases** for an agent or
  RAG project of your own.
- **Anyone who wants a working reference implementation** — not just a
  spec explainer — of ingestion, validation, graph construction, hybrid
  retrieval, and a grounded, hallucination-resistant agent, all built on
  top of OKF.

No prior knowledge of knowledge graphs, RAG, or AI agents is assumed —
those are explained from scratch in the learning path below.

## What is OKF, and why does it matter?

**Open Knowledge Format (OKF)** is a specification from Google Cloud
(v0.1, announced June 2026) for representing knowledge — descriptions
of datasets, APIs, metrics, procedures, anything a team knows about its
own systems — as **plain markdown files with a small YAML header**. No
database, no server, no SDK required to read or write it.

It exists because two audiences currently solve the same problem badly:
humans hunting across wikis/catalogs/Slack for answers, and AI agents
that need that same knowledge stuffed into their context window before
they can answer grounded in facts instead of guessing. OKF's bet is
that a common, git-diffable, human-and-agent-readable file format fixes
both at once. Full explanation, from scratch: [`docs/01-why-okf.md`](docs/01-why-okf.md).

This repository is an **independent, third-party project** — not built
or endorsed by Google — that adopts OKF as its internal knowledge
format and adds its own stricter, enterprise-oriented conventions on
top of it. Keeping that line clear (spec vs. this repo's extensions) is
a running theme throughout the docs — see
[`docs/05-frontmatter-and-fields.md`](docs/05-frontmatter-and-fields.md)
for exactly where it's drawn.

## Learning path (start here if OKF is new to you)

Read in order — each is 5–15 minutes and ends with something concrete
you did, not just read:

**Two-track mental model:** docs 00–06 are *Track A* (OKF-the-spec).
Docs 07–11 are *Track B* (this repo's stricter validation and full
pipeline).

| # | Doc | You'll be able to... |
|---|-----|------------------------|
| 00 | [Overview](docs/00-overview.md) | Tell OKF-the-spec apart from this repo's pipeline. |
| 01 | [Why OKF](docs/01-why-okf.md) | Explain the problem OKF solves, in your own words. |
| 02 | [Prerequisites](docs/02-prerequisites.md) | Confirm your machine can run everything — no API key required. |
| 03 | [Your First OKF Document](docs/03-first-okf-document.md) | Hand-write one valid OKF concept file from scratch. |
| 04 | [Bundle Structure](docs/04-bundle-structure.md) | Organize multiple concepts into a real bundle. |
| 05 | [Frontmatter & Fields](docs/05-frontmatter-and-fields.md) | Know exactly which fields the spec requires vs. what this repo adds. |
| 06 | [Links, Index, Log, Citations](docs/06-links-index-log-citations.md) | Cross-link concepts and cite sources correctly. |
| 07 | [Conformance & Validation](docs/07-conformance-and-validation.md) | Run this repo's validator and interpret every error it can raise. |
| 08 | [Real-World Workflows](docs/08-real-world-workflows.md) | Run the full ingest → validate → graph → retrieve → ask pipeline. |
| 09 | [Troubleshooting](docs/09-troubleshooting.md) | Unblock yourself on the most common first-run failures. |
| 10 | [FAQ](docs/10-faq.md) | Get quick answers to the questions beginners ask most. |
| 11 | [Next Steps](docs/11-next-steps.md) | Know where to go after finishing this repo. |

Reference-style docs (precise, no narrative — read after the path
above): [`docs/architecture.md`](docs/architecture.md),
[`docs/okf-format.md`](docs/okf-format.md),
[`docs/retrieval.md`](docs/retrieval.md),
[`docs/agent.md`](docs/agent.md),
[`docs/evaluation.md`](docs/evaluation.md).

## Problem Statement

Enterprise knowledge is distributed across API docs, runbooks, metrics
definitions, markdown notes, CSV schemas, and incident pages. Raw-document
RAG alone often fails on:
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

**No API key, no local LLM server, and no GCP account required** — the
default configuration runs fully offline with deterministic embeddings
and a rule-based agent. See [`docs/02-prerequisites.md`](docs/02-prerequisites.md)
for exactly why.

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

Prefer to run each stage by hand and see what it does? Follow
[`docs/08-real-world-workflows.md`](docs/08-real-world-workflows.md) —
every command there was run against this exact repo and its real
output is shown inline.

## Setup and Installation

### Prerequisites

- Python 3.11+
- `uv`
- `git`

Full first-time setup, including what you explicitly do **not** need
(API keys, Ollama, a GCP account): [`docs/02-prerequisites.md`](docs/02-prerequisites.md).

### Install

```bash
uv sync --extra dev --frozen
cp .env.example .env
```

Core environment defaults are defined in `.env.example` and loaded by `enterprise_okf_ai.core.settings.Settings`.

## Usage

### Full pipeline workflow

```bash
# 1. Build an OKF bundle from raw documents
uv run enterprise-okf-ai build-okf examples/enterprise_docs okf_bundle

# 2. Validate the bundle
uv run enterprise-okf-ai okf-validate --okf-dir okf_bundle

# 3. Build graph artifacts
uv run enterprise-okf-ai graph-build --okf-dir okf_bundle

# 4. Build the vector index (required before retrieval/agent commands)
uv run enterprise-okf-ai index-build --okf-dir okf_bundle

# 5. Hybrid retrieval
uv run enterprise-okf-ai retrieve-search "Which API updates order status?" --with-trace

# 6. Agent question answering
uv run enterprise-okf-ai agent-ask "Which API updates order status and what does it depend on?"
```

`retrieve-search` and `agent-ask` always read `Settings`'s default
paths (`okf_bundle/`, `vector_db/chroma/`) — build and index into those
paths as shown, or set `OKF_DIR`/`VECTOR_DIR` in `.env` to use a custom
location. Step-by-step walkthrough with real, verified output for each
command: [`docs/08-real-world-workflows.md`](docs/08-real-world-workflows.md).

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

- Local default embeddings use deterministic fallback vectors; production embeddings require provider configuration (see [`docs/11-next-steps.md`](docs/11-next-steps.md) for wiring in a real LLM/embedding provider).
- Abstention calibration is not yet strong (`abstain_accuracy = 0.5` on current benchmark).
- Sample enterprise corpus is realistic but small.
- This repo's strict validator flags any mutual concept reference (A links to B, B links to A) as a `CIRCULAR_REFERENCE` error, even though such references are entirely legitimate under the OKF spec — see [`docs/07-conformance-and-validation.md`](docs/07-conformance-and-validation.md#try-it-yourself--run-the-validator-on-both-bundles).
- Legacy compatibility package `src/okfhub/` remains in repo and can add onboarding overhead — ignore it; everything in the learning path uses `src/enterprise_okf_ai/`.

## Future Improvements

- Improve unsupported-answer calibration and add stronger abstention benchmarks.
- Add reranking and richer section-aware retrieval scoring.
- Expand benchmark suite (domain negatives, drift cases, regression thresholds).
- Add containerized deployment profiles and operational observability docs.
- Relax the strict validator's cycle detection to tolerate simple mutual references without flagging them as errors.

## Help & Support

- Beginner learning path and troubleshooting: [`docs/09-troubleshooting.md`](docs/09-troubleshooting.md), [`docs/10-faq.md`](docs/10-faq.md)
- Operational deep reference: [`HANDBOOK.md`](HANDBOOK.md)
- Deep-dive engineering blog: [`docs/blog.md`](docs/blog.md)
- Publication-ready variants:
  - Medium: [`docs/blog-medium.md`](docs/blog-medium.md)
  - LinkedIn: [`docs/blog-linkedin.md`](docs/blog-linkedin.md)
  - Substack: [`docs/blog-substack.md`](docs/blog-substack.md)
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

### OKF — the format itself

- [OKF v0.1 specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) — the source of truth for every spec claim in this repo's docs; read this before trusting any secondary description, including this README's.
- [OKF reference implementation](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) — Google's own reference agent (BigQuery-based) and HTML graph viewer; a different producer/consumer than this repo, useful for seeing spec-vs-implementation choices made differently.
- [Google Cloud Blog — "How the Open Knowledge Format can improve data sharing"](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing) (June 2026) — the original announcement and motivating context.

### Project-specific references

- Architecture notes: [`docs/architecture.md`](docs/architecture.md)
- OKF format notes (this repo's enterprise profile): [`docs/okf-format.md`](docs/okf-format.md)
- Retrieval notes: [`docs/retrieval.md`](docs/retrieval.md)
- Agent notes: [`docs/agent.md`](docs/agent.md)
- Evaluation notes: [`docs/evaluation.md`](docs/evaluation.md)
- In-depth technical blog: [`docs/blog.md`](docs/blog.md)
- End-to-end evidence artifact: [`artifacts/e2e_real_run/e2e_summary.json`](artifacts/e2e_real_run/e2e_summary.json)
- Release notes: [`RELEASE_NOTES.md`](RELEASE_NOTES.md)

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

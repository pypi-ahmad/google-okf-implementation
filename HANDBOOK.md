# enterprise-okf-ai Handbook

Operational and technical manual for onboarding, running, validating, and maintaining this repository.

## Start Here

### Who this handbook is for

- AI/ML engineers implementing or extending the pipeline
- contributors preparing production-ready changes
- operators validating end-to-end behavior before release

**New to OKF itself, not just this repo?** This handbook assumes you
already know what OKF is. If you don't, start with
[`docs/00-overview.md`](docs/00-overview.md) instead — a numbered,
zero-to-mastery learning path (`docs/00` through `docs/11`) that
teaches the format from first principles before this repo's own
conventions.

### Role-based navigation

- New contributor path: [Tutorial lane](#tutorial-lane-first-successful-run) -> [Reference lane](#reference-lane-lookup-details)
- Operator path: [How-to lane](#how-to-lane-common-operational-tasks) -> [Troubleshooting](#troubleshooting)
- Architecture/review path: [Explanation lane](#explanation-lane-why-the-system-is-designed-this-way)

## Tutorial Lane (first successful run)

Goal: run the project end-to-end and produce validated artifacts.

### Step 1: install dependencies

```bash
uv sync --extra dev --frozen
cp .env.example .env
```

### Step 2: run quality gates

```bash
UV_CACHE_DIR=.uv-cache make check
```

Expected result:
- ruff pass
- mypy pass
- pytest pass
- notebook validator pass

### Step 3: run strict end-to-end pipeline

```bash
UV_CACHE_DIR=.uv-cache make run-e2e
```

Expected summary output:
- `validation_errors = 0`
- `validation_warnings = 0`
- API checks all `200`

Artifacts produced:
- `artifacts/e2e_real_run/okf_bundle/`
- `artifacts/e2e_real_run/graph/`
- `artifacts/e2e_real_run/vector_db/`
- `artifacts/e2e_real_run/e2e_summary.json`

## How-to Lane (common operational tasks)

### Build an OKF bundle from source docs

```bash
uv run enterprise-okf-ai build-okf examples/enterprise_docs okf_bundle
```

`retrieve-search`/`agent-ask` below always read the default paths from
`Settings` (`okf_bundle/`, `vector_db/chroma/`) — build into `okf_bundle`
as shown, or set `OKF_DIR`/`VECTOR_DIR` in `.env` to point at a custom
location instead.

### Validate bundle integrity

```bash
uv run enterprise-okf-ai okf-validate --okf-dir okf_bundle
```

### Build graph artifacts

```bash
uv run enterprise-okf-ai graph-build --okf-dir okf_bundle
```

### Build the vector index

```bash
uv run enterprise-okf-ai index-build --okf-dir okf_bundle
```

Required before `retrieve-search`/`agent-ask` — they read from this
persisted index, not the bundle directly. Idempotent: re-run after any
bundle change.

### Run retrieval query with traces

```bash
uv run enterprise-okf-ai retrieve-search "Which API updates order status?" --with-trace
```

### Run agentic Q&A

```bash
uv run enterprise-okf-ai agent-ask "Which API updates order status and what does it depend on?"
```

### Run agent benchmark evaluation

```bash
uv run enterprise-okf-ai agent-eval \
  --benchmark-path examples/eval/agent_benchmark.json \
  --output-json artifacts/agent_eval_report.json
```

### Start runtime services

```bash
make run-api
make run-ui
```

### Generate handbook PDF

```bash
make handbook-pdf
```

## Reference Lane (lookup details)

### Glossary

- OKF-style bundle: markdown concept files with YAML frontmatter.
- Concept: typed knowledge object (`api`, `dataset`, `metric`, `playbook`, `table`, `glossary`).
- Hybrid retrieval: weighted combination of vector, lexical, graph, and structured signals.
- Grounded answer: response based on retrieved evidence and citations.
- Abstention: explicit unsupported-answer behavior when evidence is weak.

### Core frontmatter contract (this repo's enterprise profile)

The OKF v0.1 spec itself requires only `type`. This repo's own
generator/validator additionally require:
- `id`
- `type`
- `title`
- `description`
- `tags`
- `resource`
- `sources`
- `relationships`
- `timestamp`

See [`docs/05-frontmatter-and-fields.md`](docs/05-frontmatter-and-fields.md)
for the full spec-vs-extension breakdown — this distinction is easy to
miss and worth reading before assuming any of the above is an OKF
requirement.

### Configuration reference

Runtime settings are loaded through `enterprise_okf_ai.core.settings.Settings`.

Important settings:
- `okf_dir`
- `vector_dir`
- `graph_dir`
- `llm_provider`
- `llm_base_url`
- `llm_chat_model`
- `llm_embed_model`

Config files:
- `configs/app.yaml`
- `configs/pipeline.example.yaml`

### Module map

Canonical package: `src/enterprise_okf_ai/`

- `ingestion`: multi-format parsing + normalization
- `okf`: deterministic bundle compilation
- `validators`: strict metadata and link checks
- `graph`: graph build/export services
- `retrieval`: router + retrieval metrics wrappers
- `agent`: orchestration + agent benchmark harness
- `api`: FastAPI app factory and endpoints
- `ui`: Streamlit interface

Compatibility package:
- `src/okfhub/` (legacy compatibility surface)

### Output artifacts and interpretation

Primary outputs from strict E2E:
- `artifacts/e2e_real_run/okf_bundle/`
- `artifacts/e2e_real_run/graph/graph.json`
- `artifacts/e2e_real_run/graph/graph.graphml`
- `artifacts/e2e_real_run/graph/graph.html`
- `artifacts/e2e_real_run/vector_db/chroma.sqlite3`
- `artifacts/e2e_real_run/e2e_summary.json`

Key current metrics (from latest strict run):
- graph: `9` nodes / `17` edges
- indexing: `9` files scanned / `11` chunks indexed
- validation: `0` errors / `0` warnings
- retrieval: `result_count = 8`
- agent benchmark:
  - `total_cases = 4`
  - `avg_concept_recall = 1.0`
  - `avg_answer_support = 0.5`
  - `abstain_accuracy = 0.5`

### Community and repository health files

- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
- [`SECURITY.md`](SECURITY.md)
- [`SUPPORT.md`](SUPPORT.md)

## Explanation Lane (why the system is designed this way)

### Why OKF-style markdown

- portable and versionable in git
- human-readable and agent-consumable
- deterministic diffs for knowledge lifecycle changes

### Why strict validation before retrieval/agent

- prevents broken links from degrading graph and retrieval quality
- surfaces concept duplication and cyclic references early
- creates release-gate quality guarantees

### Why hybrid retrieval instead of vector-only

- vector retrieval captures semantic similarity
- BM25 improves exact/schema/identifier lookups
- graph signals improve relation-heavy enterprise questions
- combined scoring gives more robust behavior across query types

### Why explicit unsupported-answer logic

- reduces confident hallucinations in weak-evidence scenarios
- provides auditable safety behavior (`supported` flag and reason)

## Troubleshooting

### CLI command not found

If `enterprise-okf-ai` is unavailable in shell path:

```bash
PYTHONPATH=src uv run --no-sync python -m enterprise_okf_ai.cli.main --help
```

### Failing E2E due to stale artifacts

Delete target artifact folder and rerun strict pipeline:

```bash
rm -rf artifacts/e2e_real_run
UV_CACHE_DIR=.uv-cache make run-e2e
```

### GitHub CLI authentication issues

```bash
gh auth status
gh auth login -h github.com
```

### Non-fatal dependency warning in tests

Current tests may show a `chromadb` deprecation warning (`asyncio.iscoroutinefunction`). The run is still successful.

## Documentation Maintenance Policy

- Treat `README.md` as onboarding + quick-run surface.
- Treat `HANDBOOK.md` as operational deep reference.
- Update docs whenever command behavior, outputs, or architecture changes.
- For release candidates, regenerate and verify:
  - `make check`
  - `make run-e2e`
  - `make handbook-pdf`
- Keep major claims traceable to:
  - repository source/config,
  - executable command output,
  - official external references.

## Official References and Sources

Project references:
- Google Cloud OKF overview:
  - https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing
- OKF specification:
  - https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md

Official docs for stack used here:
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

Documentation quality guidance used in this handbook rewrite:
- GitHub README guidance:
  - https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes
- GitHub docs writing best practices:
  - https://docs.github.com/en/contributing/writing-for-github-docs/best-practices-for-github-docs
- Healthy contributions setup:
  - https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions
- GitHub Markdown syntax and linking:
  - https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax
- Diátaxis framework:
  - https://diataxis.fr/
- Write the Docs guide:
  - https://www.writethedocs.org/guide/
- Microsoft style quick start:
  - https://learn.microsoft.com/en-us/contribute/content/style-quick-start
- Microsoft headings/scannability guidance:
  - https://learn.microsoft.com/en-us/style-guide/scannable-content/headings

# Architecture

## System Goal

`enterprise-okf-ai` turns fragmented enterprise documentation into a versionable, queryable, and agent-consumable knowledge system.

## Data Flow

```text
Raw Enterprise Docs
  -> Ingestion + Normalization
  -> OKF Bundle Generation
  -> Validation + Health Reporting
  -> Knowledge Graph Build
  -> Embedding + Vector Index
  -> Hybrid Retrieval Router
  -> Tool-Calling Agent
  -> Evaluation Harness
  -> API / CLI / Streamlit
```

## Core Design Principles

- Keep knowledge portable with markdown + YAML frontmatter.
- Separate deterministic compilation from probabilistic reasoning.
- Make retrieval traceable (route selection, score breakdown, evidence citations).
- Add explicit unsupported-answer behavior instead of forced guessing.
- Treat evaluation as a first-class artifact, not an afterthought.

## Package Layout

- `enterprise_okf_ai.core`: runtime settings and common utilities
- `enterprise_okf_ai.ingestion`: multi-format document ingestion
- `enterprise_okf_ai.okf`: compiler and bundle generation
- `enterprise_okf_ai.validators`: OKF validation services
- `enterprise_okf_ai.graph`: graph build and export services
- `enterprise_okf_ai.retrieval`: hybrid retrieval and evaluation wrappers
- `enterprise_okf_ai.agent`: tool-calling orchestration and agent evaluation
- `enterprise_okf_ai.api`: FastAPI runtime surfaces
- `enterprise_okf_ai.ui`: Streamlit interactive UI
- `enterprise_okf_ai.cli`: operational CLI

## Runtime Interfaces

- CLI: `enterprise-okf-ai`
- API:
  - `POST /retrieval/search`
  - `POST /agent/ask`
  - `POST /agent/evaluate`
- UI:
  - Streamlit app at `src/enterprise_okf_ai/ui/streamlit_app.py`

## Artifact Boundaries

- OKF bundle: human-readable source of truth
- Graph artifacts: `graph.json`, `graph.graphml`, `graph.html`
- Vector artifacts: local Chroma index + idempotent manifest
- Reports: validation diagnostics, retrieval and agent benchmark summaries

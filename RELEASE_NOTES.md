# Release Notes

## v0.1.0

Initial public release of `enterprise-okf-ai`.

### Highlights

- End-to-end enterprise knowledge workflow:
  - ingestion (`PDF`, `DOCX`, `Markdown`, `CSV`, `HTML`)
  - OKF-style bundle generation
  - strict validation
  - knowledge graph construction/export
  - vector indexing with Chroma
  - hybrid retrieval router
  - tool-calling agent orchestration
- Runtime surfaces:
  - Typer CLI
  - FastAPI endpoints
  - Streamlit UI
- Quality and release hardening:
  - test suite, type checking, linting, notebook validation
  - CI workflows and pre-commit hooks

### Documentation Delivered

- Professional `README.md`
- Full project `HANDBOOK.md`
- Generated `HANDBOOK.pdf`
- Existing docs set (`docs/architecture.md`, `docs/okf-format.md`, `docs/retrieval.md`, `docs/agent.md`, `docs/evaluation.md`, `docs/release-checklist.md`)

### Verified Run Evidence (current workspace)

Validation and runtime summary from strict E2E run (`artifacts/e2e_real_run/e2e_summary.json`):

- Validation: `0` errors, `0` warnings, `0` cycles, `0` orphans
- Graph: `9` nodes, `17` edges
- Indexing: `9` files scanned, `11` chunks indexed
- API checks: `/health`, `/retrieval/search`, `/agent/ask`, `/agent/evaluate` all returned `200`
- Agent evaluation summary:
  - `total_cases = 4`
  - `avg_concept_recall = 1.0`
  - `avg_answer_support = 0.5`
  - `abstain_accuracy = 0.5`

### Known Limitations

- Local default embedding is deterministic fallback; production embeddings require provider configuration.
- Agent abstention calibration needs improvement (`abstain_accuracy = 0.5` on current benchmark).

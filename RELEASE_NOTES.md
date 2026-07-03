# Release Notes

## v0.2.0

Education-focused release: a zero-to-mastery OKF learning path, a fixed
CLI golden path, and a stale example bundle brought back in line with
the repo's own validator.

### Why this release

The previous docs set explained *this repo's pipeline* well but never
actually taught OKF — Google Cloud's Open Knowledge Format spec — from
first principles, and in places presented this repo's own stricter,
enterprise-specific field requirements as if they were the OKF spec
itself. This release fixes both: a genuine beginner-to-practitioner
learning path for OKF, and an explicit, consistent line between "what
the spec requires" and "what this repo additionally requires."

### New: zero-to-mastery learning path (`docs/00`–`docs/11`)

Twelve new numbered docs, each ending in something you actually did,
not just read — from hand-writing a spec-minimal OKF file with a text
editor through running the full ingest → validate → graph → retrieve →
ask pipeline:

- `00-overview.md`, `01-why-okf.md` — what OKF is and why it exists, grounded in the official spec.
- `02-prerequisites.md` — setup, and an explicit "no API key required" callout.
- `03-first-okf-document.md`, `04-bundle-structure.md` — hand-write and organize real OKF concepts.
- `05-frontmatter-and-fields.md` — the spec's required/recommended fields side by side with this repo's enterprise-required fields, and why they differ.
- `06-links-index-log-citations.md`, `07-conformance-and-validation.md` — cross-linking, `index.md`/`log.md`, and this repo's validator run live against two example bundles.
- `08-real-world-workflows.md` — the full six-stage pipeline, every command and output verified against this exact repository.
- `09-troubleshooting.md`, `10-faq.md`, `11-next-steps.md` — first-run failure modes, common questions, and where to go next.

Companion example: `examples/00_minimal_okf/` — a hand-authored, spec-only
bundle (no generated content) demonstrating `index.md`, `log.md`,
cross-links, citations, and the true single-field (`type`) minimum.

### Fixed: broken CLI golden path

Following the previous README's own documented sequence
(`build-okf` → `retrieve-search`) crashed with `FileNotFoundError` —
nothing in the CLI or API ever built the vector index that
`retrieve-search`/`agent-ask` require. Added a new `index-build`
command (`enterprise-okf-ai index-build --okf-dir <dir>`) wrapping the
existing `OKFVectorIndexer`, and corrected README/HANDBOOK's usage
examples to use consistent, working paths throughout.

### Fixed: stale checked-in example bundle

`examples/sample_okf_bundle/` (checked in as "the" sample bundle) failed
this repo's own `okf-validate` with multiple `CIRCULAR_REFERENCE`
errors — it predated a fix to the generator's relationship-ordering
logic and was never regenerated. Rebuilt via the existing
`scripts/build_sample_okf_bundle.py`; it now passes validation cleanly
(`0` errors, `0` cycles).

### Fixed: spec-vs-convention conflation in existing docs

`docs/okf-format.md` and `HANDBOOK.md` previously listed this repo's
9-field enterprise schema (`id`, `sources`, `relationships`, plus
spec-recommended fields made mandatory) as "the OKF frontmatter
contract." Both now explicitly label which fields come from the OKF
v0.1 spec and which are this repo's own additions, with a pointer to
the full breakdown in `docs/05-frontmatter-and-fields.md`. Also removed
a leaked internal session note from `HANDBOOK.md`'s appendix.

### Documented (not silently ignored): validator strictness limitation

This repo's validator flags any mutual concept reference (A links to B,
B links to A) as a `CIRCULAR_REFERENCE` error, even though the OKF spec
explicitly allows graph-shaped, cyclic bundles. This is now documented
as a known limitation in the README and `docs/07`, discovered and
verified by running the validator against a legitimate mutually-linked
bundle rather than assumed.

### Other changes

- Added `scripts/check_docs_links.py` and a `make docs-check-links` /
  `make check` target verifying no broken internal markdown links
  across `README.md`, `HANDBOOK.md`, and `docs/`.
- Added `knowledge_graph/*.graphml` to `.gitignore` (generated output
  was previously untracked-but-not-ignored).
- Version bumped to `0.2.0` in `pyproject.toml` and the FastAPI app.

### Known Limitations (carried forward, plus one new item)

- Local default embedding is deterministic fallback; production embeddings require provider configuration.
- Agent abstention calibration needs improvement (`abstain_accuracy = 0.5` on current benchmark).
- Strict validator over-flags legitimate mutual references as circular (see above).
- Legacy compatibility package `src/okfhub/` remains in the repo and can add onboarding overhead.

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

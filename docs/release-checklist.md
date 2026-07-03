# Release Checklist

Use this checklist before publishing `enterprise-okf-ai` to GitHub or creating a release tag.

## 1. Code Quality

- [ ] `uv sync --extra dev --frozen` succeeds on a clean environment.
- [ ] `make lint` passes.
- [ ] `make typecheck` passes.
- [ ] `make test` passes.
- [ ] No temporary debug statements or local-only hacks remain.

## 2. Notebook and Docs

- [ ] `python scripts/generate_tutorial.py` regenerates `notebooks/tutorial.ipynb`.
- [ ] `python scripts/validate_notebook.py notebooks/tutorial.ipynb` passes.
- [ ] `python scripts/check_docs_links.py` (or `make docs-check-links`) reports no broken internal links.
- [ ] `README.md` matches current CLI/API/UI commands.
- [ ] `docs/00-overview.md` through `docs/11-next-steps.md` (the zero-to-mastery learning path) are up to date.
- [ ] `docs/architecture.md`, `docs/okf-format.md`, `docs/retrieval.md`, `docs/agent.md`, and `docs/evaluation.md` are up to date.
- [ ] `docs/release-checklist.md` is reviewed and completed.

## 3. Data and Configs

- [ ] `configs/app.yaml` and `configs/pipeline.example.yaml` are valid.
- [ ] Seed manifest in `data/seed/enterprise_seed_manifest.yaml` matches `examples/` assets.
- [ ] No secrets are committed (`.env`, API keys, credentials).

## 4. Runtime Surfaces

- [ ] CLI smoke checks pass:
  - `enterprise-okf-ai --help`
  - `enterprise-okf-ai build-okf examples/enterprise_docs okf_bundle`
  - `enterprise-okf-ai okf-validate --okf-dir okf_bundle`
  - `enterprise-okf-ai graph-build --okf-dir okf_bundle`
  - `enterprise-okf-ai index-build --okf-dir okf_bundle`
  - `enterprise-okf-ai retrieve-search "Which API updates orders?" --with-trace`
  - `enterprise-okf-ai agent-ask "Which API updates order status?"`
- [ ] FastAPI starts and responds:
  - `enterprise-okf-ai serve --host 0.0.0.0 --port 8000`
  - `POST /retrieval/search` works
  - `POST /agent/ask` works
  - `POST /agent/evaluate` works
- [ ] Streamlit UI starts:
  - `make run-ui`

## 5. Packaging and Reproducibility

- [ ] `pyproject.toml` metadata is correct (name, version, classifiers, dependencies).
- [ ] `uv.lock` is committed and current.
- [ ] `uv build` succeeds.
- [ ] Install instructions in README use `--frozen` for reproducibility.

## 6. CI/CD

- [ ] `.github/workflows/ci.yml` passes on pull request.
- [ ] `.github/workflows/notebook-validation.yml` passes on notebook-related changes.
- [ ] Pre-commit hooks run cleanly:
  - `pre-commit run --all-files`

## 7. Final Publish Checks

- [ ] License is present and correct.
- [ ] Repository contains no generated binaries or cache artifacts.
- [ ] Version and changelog/release notes are prepared.
- [ ] Tag and release candidate commit are reviewed by at least one other engineer.

# 09 — Troubleshooting

Find your symptom below. Each entry says what's actually happening, not
just the fix, so you can recognize the same root cause elsewhere.

## Setup and installation

### `uv: command not found`

`uv` isn't installed or isn't on your `PATH` yet. Install it per
[02 — Prerequisites](02-prerequisites.md), then open a new shell (the
installer updates your shell profile, which an already-open terminal
won't have picked up).

### CLI command not found (`enterprise-okf-ai: command not found`)

`uv sync` didn't complete, or you're invoking the binary outside the
project's virtual environment. Two working alternatives:

```bash
uv run enterprise-okf-ai --help
# or, if the console script itself is misbehaving:
PYTHONPATH=src uv run --no-sync python -m enterprise_okf_ai.cli.main --help
```

If neither works, re-run `uv sync --extra dev --frozen` and check for
errors in its output before retrying.

### `ModuleNotFoundError: No module named 'ingest'` (or `validators`, `graph`, `generator`, `rag`, `vector_db`)

This repo's source tree splits code into small top-level packages
(`src/ingest/`, `src/validators/`, `src/graph/`, ...) that
`src/enterprise_okf_ai/` imports directly — see
[`docs/architecture.md`](architecture.md#package-layout). They're only
importable when `src/` is on `PYTHONPATH`. `uv run enterprise-okf-ai
...` handles this automatically via the editable install; you'll only
hit this error if you invoke a script directly with plain `python`
instead of `uv run`, or bypass the installed console script. Fix:
prefix the command with `PYTHONPATH=src`, or use `uv run` as shown
throughout this guide.

## Running the pipeline

### `FileNotFoundError: OKF directory not found: .../okf_bundle`

This means `retrieve-search` or `agent-ask` looked for a bundle at the
default path (`okf_bundle/` under the project root, from `Settings`)
and didn't find one. Two likely causes:

1. You haven't run `build-okf` yet, or you built into a different
   directory than the default. Fix: `uv run enterprise-okf-ai build-okf
   examples/enterprise_docs okf_bundle` (see
   [08 — Real-World Workflows](08-real-world-workflows.md)).
2. You built into a custom directory (e.g.
   `artifacts/local_okf_bundle`) — `retrieve-search`/`agent-ask` don't
   take an `--okf-dir` flag; they always read `Settings().okf_dir`.
   Either build straight into `okf_bundle/` (simplest), or point
   `Settings` elsewhere by setting `OKF_DIR=artifacts/local_okf_bundle`
   (and matching `VECTOR_DIR`) in your `.env` file before running them.

### `retrieve-search` or `agent-ask` returns no results / low-confidence "not supported" answers

You almost certainly skipped `index-build`. `retrieve-search` and
`agent-ask` read from the **persisted vector index**, not the bundle
directly — if the index doesn't exist yet or is stale relative to the
bundle, results will be empty or wrong. Run:

```bash
uv run enterprise-okf-ai index-build --okf-dir okf_bundle
```

then retry. This is a new command added in this release specifically
to close this gap — see the callout in
[08 — Real-World Workflows](08-real-world-workflows.md).

### `okf-validate` reports `MISSING_MANDATORY_FIELDS` on a bundle I wrote by hand

Expected if you followed [03](03-first-okf-document.md)/[04](04-bundle-structure.md)
literally — those pages teach the *spec's* minimal fields. This repo's
validator checks a stricter, larger set. Read
[05 — Frontmatter & Fields](05-frontmatter-and-fields.md) for the exact
list, or feed raw documents through `build-okf` instead of hand-writing
the enterprise profile yourself.

### `okf-validate` reports `CIRCULAR_REFERENCE` on a bundle with no obvious loop

Check whether two concepts simply reference *each other* (A links to B,
B links to A). This validator treats any mutual reference as a cycle,
even a two-node one — a known strictness limitation, not a sign your
bundle is actually broken. Details: [07 — Conformance & Validation](07-conformance-and-validation.md#try-it-yourself--run-the-validator-on-both-bundles).

### Invalid frontmatter block / YAML parse errors

Almost always one of:

- Tabs instead of spaces for indentation (YAML forbids tabs).
- A missing closing `---` line.
- An unquoted string containing a `:` (quote it:
  `description: "Note: important"`).

See the verification one-liner in
[03 — Your First OKF Document](03-first-okf-document.md#verify-it-parses)
to isolate the exact problem before re-reading the file by eye.

### `chromadb` deprecation warning during tests or indexing

You may see a warning referencing `asyncio.iscoroutinefunction`. This
is a known, non-fatal warning from the `chromadb` dependency itself —
it doesn't affect indexing or retrieval correctness and can be ignored.

### Stale artifacts after changing the pipeline code or sample data

```bash
rm -rf okf_bundle vector_db/chroma knowledge_graph artifacts/e2e_real_run
uv run enterprise-okf-ai build-okf examples/enterprise_docs okf_bundle
```

Then redo steps 2–4 from
[08 — Real-World Workflows](08-real-world-workflows.md). `index-build`
is idempotent and diffs against a checksum manifest, but a fully clean
rebuild is the fastest way to rule out stale-state issues while
debugging.

## `make check` / CI

### `make check` fails on `mypy` or `ruff` after you edited code

Run the two checks individually to isolate which one is unhappy:

```bash
uv run ruff check src tests scripts
uv run mypy src/enterprise_okf_ai --python-version 3.12
```

Note `mypy` is scoped to `src/enterprise_okf_ai` only — the flat
top-level packages (`src/ingest`, `src/validators`, etc.) and the
legacy `src/okfhub/` package are not type-checked by `make check`.

### `gh auth` errors when following the release process

Only relevant if you're preparing a release (see
[`RELEASE_NOTES.md`](../RELEASE_NOTES.md)), not for running the
tutorial path:

```bash
gh auth status
gh auth login -h github.com
```

## Still stuck?

Check [10 — FAQ](10-faq.md) next, then
[`HANDBOOK.md`](../HANDBOOK.md)'s Reference and Explanation lanes for
deeper detail on any one subsystem.

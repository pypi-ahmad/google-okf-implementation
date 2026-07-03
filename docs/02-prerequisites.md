# 02 — Prerequisites

## What you need installed

| Requirement | Version | Why | Check with |
|---|---|---|---|
| Python | 3.11 or newer | Runtime for the whole pipeline. | `python3 --version` |
| [`uv`](https://docs.astral.sh/uv/) | any recent | Dependency management and running commands (`uv run ...`). Replaces manually managing a virtualenv + pip. | `uv --version` |
| `git` | any recent | Cloning the repo, and the version-control workflow OKF bundles are designed around. | `git --version` |
| `make` | any recent | Convenience wrapper around common commands (optional — every `make` target has a plain `uv run` equivalent shown alongside it). | `make --version` |

If `uv` is missing, install it with the official script rather than
`pip install uv` (see [uv's installation docs](https://docs.astral.sh/uv/getting-started/installation/)):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Platform note (unverified for this repo specifically):** the commands
in this documentation are written for Linux and macOS shells. They
should work under WSL on Windows since `uv`, Python, and `git` all
support it, but this has not been tested from within this project —
if you hit a Windows-specific issue, prefer running from WSL first
before troubleshooting further.

## What you do *not* need

This is worth stating explicitly, because it's the single most common
point of confusion on a first run:

- **No OpenAI, Anthropic, or Google API key is required** to complete
  docs 00–09 of this learning path. The default configuration
  (`.env.example`, `configs/app.yaml`) points at a local Ollama server
  and a deterministic fallback embedding function
  (`enterprise_okf_ai.core.embeddings.deterministic_embedding`), and the
  CLI's `agent-ask`/`agent-eval` commands run the agent with `llm=None`
  — meaning answers are composed from retrieved evidence with simple,
  rule-based logic, not by calling a hosted LLM. This is intentional: it
  makes the whole pipeline runnable offline, for free, on a laptop.
- **No Ollama installation is required either**, for the same reason —
  the default embedding path never calls it. `LLM_PROVIDER=ollama` in
  `.env.example` documents *how you would* plug in a real local model
  later (see [11 — Next Steps](11-next-steps.md)), it isn't exercised by
  the default commands in this guide.
- **No GCP account, BigQuery access, or Google credentials** — this repo
  is independent of Google's own OKF reference agent, which does use
  BigQuery. Nothing here calls a Google API.

If a command in this guide ever seems to want a credential you don't
have, that's a signal to check [09 — Troubleshooting](09-troubleshooting.md)
before assuming you're missing a required setup step.

## Install the project

```bash
git clone https://github.com/pypi-ahmad/google-okf-implementation.git
cd google-okf-implementation
uv sync --extra dev --frozen
cp .env.example .env
```

`uv sync --extra dev --frozen` reads `uv.lock` and creates a `.venv/`
with every pinned dependency — `--frozen` means it will refuse to
silently update the lockfile, so what you install matches exactly what
CI tests against.

### Verify the install

```bash
uv run enterprise-okf-ai --help
```

**Expected output:** a Typer-generated help screen listing commands
(`ingest`, `build-okf`, `okf-validate`, `graph-build`, `retrieve-search`,
`agent-ask`, `agent-eval`, `serve`, ...). If you see that, your
environment is ready and you can move on to
[03 — Your First OKF Document](03-first-okf-document.md).

If instead you see `command not found` or an import error, go straight
to [09 — Troubleshooting](09-troubleshooting.md#cli-command-not-found) —
don't debug it from scratch, the fix is almost always one of two known
causes.

## A note on what this repo assumes you already know

This learning path assumes basic comfort with:

- Running commands in a terminal.
- Reading YAML (`key: value` pairs) and Markdown (`#` headings, `[text](link)`
  links) — if either is new to you, [CommonMark's own 5-minute
  tutorial](https://commonmark.org/help/tutorial/) and
  [Learn YAML in Y minutes](https://learnxinyminutes.com/docs/yaml/) are
  good five-minute primers.
- A very basic idea of what `git clone`, `git status`, and `git diff` do.

It does **not** assume any prior exposure to knowledge graphs,
retrieval-augmented generation (RAG), or AI agents — those are
explained from scratch in [08 — Real-World Workflows](08-real-world-workflows.md)
when they first become relevant.

Next: [03 — Your First OKF Document](03-first-okf-document.md).

# Contributing

Thanks for contributing to `enterprise-okf-ai`.

## Before You Start

- Read [`README.md`](README.md) for project overview and quick start.
- Read [`HANDBOOK.md`](HANDBOOK.md) for operational details.
- Use the canonical package in `src/enterprise_okf_ai/` for new work.

## Development Setup

```bash
uv sync --extra dev --frozen
cp .env.example .env
```

## Contribution Workflow

1. Open an issue describing the bug/feature proposal.
2. Keep changes scoped and testable.
3. Update docs when behavior changes.
4. Run quality gates before opening a PR.

## Required Checks

```bash
UV_CACHE_DIR=.uv-cache make check
UV_CACHE_DIR=.uv-cache make run-e2e
```

If you update handbook content:

```bash
make handbook-pdf
```

## Coding and Documentation Standards

- Python with type hints.
- Keep APIs explicit and deterministic where possible.
- Prefer official/primary sources for technical claims.
- Do not include fabricated metrics, outputs, or references.

## Pull Request Expectations

A good PR should include:
- problem statement
- what changed
- how it was verified (commands + outcomes)
- known limitations or follow-up work

## Security

Please do not open public issues for sensitive vulnerabilities. See [`SECURITY.md`](SECURITY.md).

## Conduct

All contributors are expected to follow [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

# 00 — Overview: What Is OKF, and What Is This Repo?

> **Read this first.** Every other document in `docs/` builds on the two
> or three ideas explained here.

## The one-paragraph version

**OKF (Open Knowledge Format)** is a specification from Google Cloud,
published June 2026, that defines how to write down "knowledge" —
descriptions of datasets, APIs, metrics, procedures, anything a team
knows about its own systems — as plain markdown files with a small YAML
header. Nothing more. No database, no server, no SDK to install just to
read it. **This repository, `enterprise-okf-ai`, is a working system
that *uses* OKF**: it turns messy enterprise documents (PDFs, DOCX,
CSVs, wiki pages) into an OKF-style bundle, checks that bundle for
mistakes, builds a graph out of it, and answers questions over it with
an AI agent.

If you take away one distinction from this page, take away this one:

| | |
|---|---|
| **OKF** | A *file format spec*. Markdown + YAML frontmatter. You could write a conformant OKF bundle by hand in a text editor and never run a line of code. |
| **`enterprise-okf-ai` (this repo)** | A *pipeline* that produces, validates, and consumes OKF bundles automatically, plus adds its own extra rules on top of the format for enterprise use. |

Confusing those two things is the single most common way to misread this
project, so the whole `docs/00`–`docs/11` sequence keeps them visually
separate: spec-only material has no mention of Python, CLI flags, or
this repo's code; repo-specific material says so explicitly.

## Who this is for

- You have **never heard of OKF** and want to understand it from zero,
  independent of any particular tool.
- You've skimmed the [README](../README.md) and want the guided,
  step-by-step version instead of the reference-style summary.
- You're evaluating whether OKF-style markdown knowledge bases fit a
  problem you have (fragmented docs, agents that need grounded context,
  a catalog that's locked in a proprietary tool).

No prior knowledge of knowledge graphs, RAG (retrieval-augmented
generation), or AI agents is assumed. Each of those terms is defined in
plain English the first time it matters.

## The learning path

Read these in order. Each one is short (5–15 minutes) and ends with
something concrete you did, not just read.

**Two tracks:** docs 00–06 are about OKF v0.1 *as a spec you can use
without this repo*. Docs 07–11 are about *this repository's stricter
enterprise profile and pipeline* built on top of OKF.

| # | Doc | You'll be able to... |
|---|-----|------------------------|
| 00 | *(this page)* | Tell OKF-the-spec apart from this repo's pipeline. |
| 01 | [Why OKF](01-why-okf.md) | Explain the problem OKF solves, in your own words. |
| 02 | [Prerequisites](02-prerequisites.md) | Confirm your machine can run the examples — no API key required. |
| 03 | [Your First OKF Document](03-first-okf-document.md) | Hand-write one valid OKF concept file from scratch. |
| 04 | [Bundle Structure](04-bundle-structure.md) | Organize multiple concepts into a real bundle. |
| 05 | [Frontmatter & Fields](05-frontmatter-and-fields.md) | Know exactly which fields the spec requires vs. what this repo adds. |
| 06 | [Links, Index, Log, Citations](06-links-index-log-citations.md) | Cross-link concepts and cite external sources correctly. |
| 07 | [Conformance & Validation](07-conformance-and-validation.md) | Run this repo's validator and interpret every error it can raise. |
| 08 | [Real-World Workflows](08-real-world-workflows.md) | Run the full ingest → validate → graph → retrieve → ask pipeline. |
| 09 | [Troubleshooting](09-troubleshooting.md) | Unblock yourself on the most common first-run failures. |
| 10 | [FAQ](10-faq.md) | Get quick answers to the questions beginners ask most. |
| 11 | [Next Steps](11-next-steps.md) | Know where to go after finishing this repo. |

There's a second tier of documents — [`architecture.md`](architecture.md),
[`okf-format.md`](okf-format.md), [`retrieval.md`](retrieval.md),
[`agent.md`](agent.md), [`evaluation.md`](evaluation.md) — written as
**reference material**, not tutorials. Come back to those once you've
finished the numbered sequence and want the precise, no-narrative
technical detail on one subsystem.

## Where OKF comes from

OKF is defined in the `okf/` directory of Google Cloud's public
`knowledge-catalog` repository, alongside a reference agent that
produces bundles and a viewer that renders them:

- Spec: [`GoogleCloudPlatform/knowledge-catalog/okf/SPEC.md`](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) — the source of truth for every spec claim in this repo's docs.
- Reference implementation: [`GoogleCloudPlatform/knowledge-catalog/okf/`](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) — README, sample bundles, and an HTML graph viewer.
- Announcement: [Google Cloud Blog — "How the Open Knowledge Format can improve data sharing"](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing) (June 2026).

This repo is an independent, third-party project. It is **not** built or
endorsed by Google — it's one example of building a real application on
top of an OKF-shaped knowledge layer.

Next: [01 — Why OKF](01-why-okf.md).

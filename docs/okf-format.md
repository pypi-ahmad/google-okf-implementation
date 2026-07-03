# OKF Format Guide (This Repo's Enterprise Profile)

> **Tutorial-first version of this material:** if you haven't already,
> read [`docs/00-overview.md`](00-overview.md) through
> [`docs/07-conformance-and-validation.md`](07-conformance-and-validation.md)
> first. Those pages teach OKF v0.1 — the actual Google Cloud spec —
> from zero, and explicitly separate spec requirements from this
> repo's own conventions. This page is the terse reference version of
> that same distinction, for after you've read the tutorial.

## Why OKF

[Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
is Google Cloud's v0.1 specification for representing knowledge as
portable markdown documents with YAML frontmatter. This project
generates and consumes bundles that are OKF-conformant but layer
additional, **repo-specific** required fields on top of the spec for
enterprise provenance and graph-building needs — see
[`docs/05-frontmatter-and-fields.md`](05-frontmatter-and-fields.md) for
the full spec-vs-extension breakdown. Nothing below this line is part
of the OKF spec itself unless explicitly labeled as such.

## Bundle Structure (this repo's generator output)

```text
okf_bundle/
  apis/
  datasets/
  metrics/
  playbooks/
  tables/
  glossary/
  index.md               <- bundle-root index (OKF reserved filename)
  bundle_manifest.yaml
```

Each concept is one markdown file under its typed directory. The
bundle-root `index.md` includes an optional `okf_version: "0.1"`
declaration in its frontmatter (the only place the spec permits
frontmatter in an `index.md`).

## Frontmatter Contract (this repo's enterprise profile — not the OKF spec)

The OKF v0.1 spec requires only `type`, with `title`, `description`,
`resource`, `tags`, and `timestamp` merely recommended. This repo's
generator and validator additionally require every field below —
see [`docs/05-frontmatter-and-fields.md`](05-frontmatter-and-fields.md)
for why:

- `id` — repo extension
- `type` — **the one spec-required field**
- `title` — spec-recommended, repo-required
- `description` — spec-recommended, repo-required
- `tags` — spec-recommended, repo-required
- `resource` — spec-recommended, repo-required
- `sources` — repo extension
- `relationships` — repo extension
- `timestamp` — spec-recommended, repo-required

Example:

```yaml
---
id: api:orders-api
type: api
title: Orders API
description: PATCH endpoint for updating order state.
tags: [api, orders]
resource: apis/orders_api.md
sources:
  - apis/orders_api.md
relationships:
  - type: references
    target_id: dataset:customer-profile-dataset
    target_type: dataset
    target_title: Customer Profile Dataset
    path: datasets/customer-profile-dataset.md
timestamp: "2026-07-03T00:00:00+00:00"
---
```

## Relationship Semantics

`relationships` encode explicit edges used by:

- validator checks (`broken links`, `orphans`, `cycles`)
- graph construction
- graph-aware retrieval and agent reasoning

## Determinism and Reproducibility

The compiler is deterministic:

- stable concept typing and slugging
- deduplication of duplicate concepts
- reproducible markdown output for git diffs

This allows CI to treat knowledge changes like code changes.

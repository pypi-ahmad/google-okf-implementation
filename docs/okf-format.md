# OKF Format Guide

## Why OKF

Open Knowledge Format (OKF-style) standardizes enterprise knowledge into portable markdown documents with structured YAML frontmatter. This project uses OKF-style bundles to make data easy for both humans and AI systems to consume.

## Bundle Structure

```text
okf_bundle/
  apis/
  datasets/
  metrics/
  playbooks/
  tables/
  glossary/
  README.md
  bundle_manifest.yaml
```

Each concept is one markdown file under its typed directory.

## Frontmatter Contract

Every concept document includes these required fields:

- `id`
- `type`
- `title`
- `description`
- `tags`
- `resource`
- `sources`
- `relationships`
- `timestamp`

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

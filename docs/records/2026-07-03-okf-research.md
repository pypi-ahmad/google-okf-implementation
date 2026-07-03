# 2026-07-03 OKF Research Notes (Primary Sources)

This record summarizes the OKF v0.1 spec and official context used to keep repository docs accurate.

## Primary Sources

- OKF v0.1 spec (source of truth): `GoogleCloudPlatform/knowledge-catalog/okf/SPEC.md`
  - <https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md>
- OKF repository README (reference implementations and usage): `GoogleCloudPlatform/knowledge-catalog/okf/README.md`
  - <https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/README.md>
- Google Cloud announcement (motivation + what ships with the spec):
  - <https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing>

## Spec Facts (OKF v0.1)

- OKF is intentionally minimal: a directory tree of markdown files with YAML frontmatter; no required tooling.
- A conformant bundle requires:
  - every non-reserved `.md` has parseable YAML frontmatter
  - every frontmatter block has a non-empty `type`
  - reserved files (`index.md`, `log.md`) follow their defined structures when present
- Reserved filenames are exactly:
  - `index.md` (progressive disclosure listing)
  - `log.md` (update history)
- `index.md` frontmatter is not generally allowed; the only spec-permitted exception is:
  - bundle-root `index.md` may carry frontmatter declaring `okf_version: "0.1"`
- Consumers must be permissive: missing recommended fields, unknown types, unknown keys, broken links, and missing `index.md` are explicitly not conformance failures.

## Official Context (Motivation + Ecosystem)

From the announcement and OKF repo README:

- OKF is positioned as a **format**, not a platform: producer/consumer independence and portability matter more than a single hosted service.
- Google ships reference producer/consumer implementations and sample bundles to make the format concrete, but they are examples, not requirements of the format.

## Implications for This Repository

- This repository must treat OKF-the-spec as minimal and extension-friendly.
- Any stricter schema (extra required frontmatter keys, enforced link integrity, cycle rules, etc.) must be clearly labeled as a repo-specific profile.
- If the repo claims it produces “OKF-conformant” bundles, the generated bundle shape must obey the spec’s reserved-file and conformance rules.


# 05 — Frontmatter & Fields: Spec vs. This Repo's Extensions

This is the most important reference page in the whole learning path.
An earlier version of this project's docs described this repo's
9-field enterprise schema as *"the OKF frontmatter contract,"* which
blurred the line between what OKF v0.1 actually requires and what this
specific pipeline additionally demands. This page draws that line
explicitly and permanently.

## OKF v0.1 — the actual spec

Per [SPEC.md §4.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md#41-frontmatter):

| Field | Status |
|---|---|
| `type` | **Required.** The only mandatory field in the entire spec. |
| `title` | Recommended. |
| `description` | Recommended. |
| `resource` | Recommended, when the concept describes a real asset. |
| `tags` | Recommended. |
| `timestamp` | Recommended. |
| *(anything else)* | Explicitly allowed as a producer-defined extension. Consumers MUST tolerate unknown keys. |

And conformance (spec §9) is deliberately loose: a bundle is conformant
if every non-reserved `.md` file has parseable frontmatter with a
non-empty `type`. The spec goes out of its way to say consumers **must
not** reject a bundle for missing optional fields, unknown `type`
values, unknown extra keys, broken links, or a missing `index.md`.

## `enterprise-okf-ai`'s enterprise profile — what this repo adds

This repo's bundle generator
([`src/enterprise_okf_ai/okf/bundle_generator.py`](../src/enterprise_okf_ai/okf/bundle_generator.py))
and strict validator
([`src/validators/okf_validator.py`](../src/validators/okf_validator.py))
both enforce a **stricter, enterprise-specific profile** built on top of
OKF. Every field below is a **project convention, not a spec
requirement**:

| Field | What it is | Why this repo requires it |
|---|---|---|
| `id` | A stable `type:slug` identifier (e.g. `api:orders-api`), independent of file path. | Lets the validator detect duplicate concepts even if two files describe the same thing under different filenames. |
| `sources` | List of raw source document paths this concept was derived from. | Enterprise provenance: every generated fact must trace back to an original document for audit purposes. |
| `relationships` | A structured list of typed edges (`type`, `target_id`, `target_type`, `target_title`, `path`) instead of relying only on markdown links in the body. | Makes graph construction ([`enterprise_okf_ai.graph`](../src/enterprise_okf_ai/graph/builder.py)) deterministic and independent of prose formatting. |

`title`, `description`, `tags`, `resource`, and `timestamp` are also
**required** here (not just recommended) — see
[`_REQUIRED_FRONTMATTER_KEYS`](../src/enterprise_okf_ai/okf/bundle_generator.py)
and [`MANDATORY_FIELDS`](../src/validators/okf_validator.py) in the
source.

### Side-by-side

| Field | OKF v0.1 spec | This repo's generator/validator |
|---|---|---|
| `type` | Required | Required |
| `title` | Recommended | **Required** |
| `description` | Recommended | **Required** |
| `resource` | Recommended | **Required** (empty string if not applicable) |
| `tags` | Recommended | **Required** (empty list allowed) |
| `timestamp` | Recommended | **Required** |
| `id` | Not defined by spec | **Required** — repo extension |
| `sources` | Not defined by spec | **Required** — repo extension |
| `relationships` | Not defined by spec (use body links instead) | **Required** — repo extension |

### Why this repo is stricter than the spec

The spec's permissiveness makes sense for open, cross-organization
knowledge sharing where a partial or evolving bundle should still be
usable. This repo instead treats a bundle as a **build artifact that
gates a production pipeline** (retrieval index, knowledge graph, agent
answers) — see [`docs/architecture.md`](architecture.md). For that use
case, silently tolerating a missing `description` or an untraceable
`sources` list means degraded retrieval quality with no error to catch
it in CI. The tradeoff this repo makes is: **give up some of OKF's
open-ended flexibility, in exchange for a validator that can fail a
build the moment quality regresses.** [07 — Conformance & Validation](07-conformance-and-validation.md)
covers exactly what that validator checks.

### Are enterprise-profile bundles still valid OKF?

Yes. Every field this repo requires beyond the spec is an *additional*
key on top of a document that still has `type`, still uses markdown
links in the body, and still round-trips through any spec-compliant
consumer (a viewer or another team's agent) without those tools needing
to understand `id`, `sources`, or `relationships` — they'd simply be
extra frontmatter keys a lenient consumer ignores, per spec §4.1's
"Extensions" clause.

Note: OKF reserves `index.md` and `log.md` (spec §3.1). This repo's
generator writes a bundle-root `index.md` and includes an optional
`okf_version: "0.1"` declaration there (spec §11). If you create a
bundle-root `README.md` instead, it's treated as a normal concept file
under the spec and must have frontmatter like any other concept.

## Practical rule of thumb

- **Writing OKF by hand, or for sharing outside this repo?** Follow the
  spec table at the top of this page. `type` required, everything else
  optional-but-recommended.
- **Feeding documents into this repo's `build-okf` command?** The
  generator produces the enterprise profile automatically — you don't
  write the extra fields yourself, the pipeline derives them from your
  source documents (see [08 — Real-World Workflows](08-real-world-workflows.md)).
- **Writing a bundle by hand that this repo's `okf-validate` command
  will check?** You need the full enterprise profile, or the validator
  will report `MISSING_MANDATORY_FIELDS` — this is expected, not a bug;
  it's a stricter gate by design.

Next: [06 — Links, Index, Log, Citations](06-links-index-log-citations.md).

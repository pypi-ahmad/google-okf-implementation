# 07 — Conformance & Validation

## Two different bars, on purpose

By now you've seen both fields ([05](05-frontmatter-and-fields.md)) and
the fact that broken links are explicitly tolerated by the spec
([06](06-links-index-log-citations.md)). Validation is where that
difference becomes concrete and *runnable*: OKF v0.1's conformance bar
is deliberately low, and this repo's `okf-validate` command deliberately
checks something much stricter on top of it.

### OKF v0.1 conformance (the spec's own bar)

Per [SPEC.md §9](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md#9-conformance),
a bundle is conformant if, and only if:

1. Every non-reserved `.md` file has parseable YAML frontmatter.
2. Every frontmatter block has a non-empty `type`.
3. Every `index.md`/`log.md` present follows the shape in spec §6/§7.

That's it. Missing optional fields, unknown `type` values, broken links,
and missing `index.md` files are all explicitly **not** conformance
failures.

You can check this spec-level bar directly with the CLI:

```bash
uv run enterprise-okf-ai okf-spec-validate --okf-dir examples/00_minimal_okf
```

**Expected output:** `"passed": true` with `errors: 0`. This command is
*only* the OKF v0.1 conformance rules; it does not apply any of this
repo's extra enterprise requirements.

### This repo's strict validator (an additional, stricter gate)

`enterprise-okf-ai okf-validate` runs
[`OKFValidator`](../src/validators/okf_validator.py), which checks all of
the above *plus*:

| Check | Severity | What it catches |
|---|---|---|
| `MISSING_MANDATORY_FIELDS` | error | Any of this repo's [enterprise-required fields](05-frontmatter-and-fields.md) absent. |
| `DUPLICATE_CONCEPT_DEFINITION` | error | Two files claim the same `id`, or the same `(type, title)` pair. |
| `BROKEN_INTERNAL_LINK` | error | A markdown link or `relationships` entry points at a file that doesn't exist. |
| `CIRCULAR_REFERENCE` | error | The link graph contains a cycle (see caveat below). |
| `ORPHAN_DOCUMENT` | warning | A concept has zero inbound *and* zero outbound internal links. |

None of these five checks come from the OKF spec — they're this
project's own enterprise quality gate, designed to fail a CI build the
moment a generated bundle would degrade retrieval or graph quality.

## Try it yourself — run the validator on both bundles

### A spec-conformant bundle can still fail this repo's stricter gate

```bash
uv run enterprise-okf-ai okf-validate --okf-dir examples/00_minimal_okf
```

Real output from this exact command, run against the bundle from
[04](04-bundle-structure.md):

```json
{
  "passed": false,
  "stats": {
    "files_scanned": 3, "documents_parsed": 3,
    "errors": 4, "warnings": 0,
    "edges": 4, "cycles": 1, "orphans": 0,
    "duplicate_concepts": 0, "broken_links": 0
  },
  "issues": [
    {"severity": "error", "code": "MISSING_MANDATORY_FIELDS",
     "file_path": "datasets/web_traffic.md",
     "message": "Missing mandatory frontmatter fields: id, sources, relationships"},
    {"severity": "error", "code": "MISSING_MANDATORY_FIELDS",
     "file_path": "metrics/weekly_active_users.md",
     "message": "Missing mandatory frontmatter fields: id, resource, sources, relationships"},
    {"severity": "error", "code": "MISSING_MANDATORY_FIELDS",
     "file_path": "playbooks/first_response.md",
     "message": "Missing mandatory frontmatter fields: id, title, description, tags, resource, sources, relationships, timestamp"},
    {"severity": "error", "code": "CIRCULAR_REFERENCE",
     "message": "Circular reference detected: datasets/web_traffic.md -> metrics/weekly_active_users.md"}
  ]
}
```

**This is expected, not a bug in the example.** The bundle is fully
spec-conformant — every file has a valid `type` — but fails this repo's
enterprise profile for two reasons worth understanding separately:

1. **`MISSING_MANDATORY_FIELDS`** — exactly what [05](05-frontmatter-and-fields.md)
   predicted: the bundle only has spec-recommended fields, not this
   repo's required `id`/`sources`/`relationships`.
2. **`CIRCULAR_REFERENCE`** — the dataset says "used to compute
   `/metrics/weekly_active_users.md`" and the metric links back with
   "computed from `/datasets/web_traffic.md`." That mutual reference
   is a completely ordinary, legitimate pattern — and it is exactly what
   this validator's cycle detector flags, because it treats *any*
   directed loop in the link graph as a `CIRCULAR_REFERENCE`, including
   a simple two-concept mutual reference. Know this going in: if you
   hand-write a bundle for this repo's strict validator, keep
   cross-references one-directional, or expect this error on mutual
   references. This is a real, verified limitation of the current
   validator, not something the OKF spec asks for — the spec explicitly
   allows a bundle to be "graph-shaped, not just tree-shaped."

### A bundle built to satisfy this repo's own profile

```bash
uv run enterprise-okf-ai okf-validate --okf-dir examples/sample_okf_bundle
```

```json
{
  "passed": true,
  "stats": {
    "files_scanned": 9, "documents_parsed": 9,
    "errors": 0, "warnings": 0,
    "edges": 34, "cycles": 0, "orphans": 0,
    "duplicate_concepts": 0, "broken_links": 0
  },
  "issues": []
}
```

This bundle was produced by this repo's own `build-okf` generator (see
[08](08-real-world-workflows.md)), which fills in every enterprise field
automatically and orders relationships to avoid direct cycles — that's
why it passes cleanly.

**How to verify success on your own machine:** both commands above
should print `"passed": true`/`false` exactly as shown, since bundle
generation and validation in this repo are deterministic
([`docs/okf-format.md`](okf-format.md#determinism-and-reproducibility)).
If your numbers differ, check [09 — Troubleshooting](09-troubleshooting.md).

## Interpreting a validation report

- **`errors` must be zero** before a bundle should feed the graph or
  retrieval stages — this repo's `make run-e2e` pipeline gates on
  exactly that.
- **`warnings`** (currently only `ORPHAN_DOCUMENT`) don't block the
  pipeline but flag concepts nothing else links to — often a sign a
  relationship was missed, not necessarily a problem.
- **`cycles`**, per the caveat above, will trigger on any mutual
  reference, not only on pathological recursive structures — treat a
  nonzero `cycles` count as "go look," not "definitely broken."

Next: [08 — Real-World Workflows](08-real-world-workflows.md), where
you'll run the generator that produces bundles like
`examples/sample_okf_bundle` from raw documents instead of by hand.

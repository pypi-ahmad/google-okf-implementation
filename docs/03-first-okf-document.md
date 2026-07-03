# 03 — Your First OKF Document

Goal: hand-write one valid OKF concept document from nothing, using only
a text editor. No CLI command in this project is required to do this —
that's the point of the format.

## Step 1 — the absolute minimum

Create a new file anywhere, call it `hello.md`, and type exactly this:

```markdown
---
type: Note
---

# Hello OKF

This is the smallest possible valid OKF concept document.
```

That's a **complete, spec-conformant OKF concept document.** Per
[SPEC.md §9, "Conformance"](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md#9-conformance),
a bundle is conformant if every concept file has parseable YAML
frontmatter with a non-empty `type` field. Nothing else is mandated by
the spec — not a title, not a description, not a timestamp.

You can see the same idea already committed in this repo at
[`examples/00_minimal_okf/playbooks/first_response.md`](../examples/00_minimal_okf/playbooks/first_response.md) —
open it now and confirm it really does have only one frontmatter key.

## Step 2 — understand the two parts

Every concept document has exactly two parts:

```markdown
---
type: Note              <- 1. Frontmatter: YAML, between two `---` lines
---

# Hello OKF              <- 2. Body: plain markdown, everything after
This is the smallest...     the closing `---`
```

- **Frontmatter** is metadata a machine reads without parsing prose:
  what kind of thing is this (`type`), and optionally its title,
  description, tags, and so on.
- **Body** is what a human (or an LLM with the file in its context
  window) actually reads to understand the concept.

Both delimiters must be exactly `---` alone on their own line — not
`----`, not `- - -`. This is the single most common typo when writing
OKF by hand; see [09 — Troubleshooting](09-troubleshooting.md#invalid-frontmatter-block)
if a tool complains about your frontmatter.

## Step 3 — add the recommended fields

`type` is all the spec *requires*, but a bare `type` gives a consumer
almost nothing to work with. The spec recommends five more fields, in
priority order (see [SPEC.md §4.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md#41-frontmatter)):

```markdown
---
type: Dataset
title: Website Traffic
description: Raw pageview and session events collected from the marketing site.
resource: https://example.com/warehouse/web_traffic
tags: [web, analytics, raw]
timestamp: 2026-06-15T09:00:00Z
---

Raw event stream capturing every pageview and session on the marketing
site.
```

Field by field:

| Field | Meaning | Required by spec? |
|---|---|---|
| `type` | What kind of thing this is. Free text — you choose the vocabulary (`Dataset`, `API Endpoint`, `Metric`, anything). | **Yes** |
| `title` | Human-readable name. If missing, consumers fall back to the filename. | No |
| `description` | One sentence a search result or index entry can show. | No |
| `resource` | A URI for the real-world thing this describes, if it's bound to one (a table, a dashboard). Omit entirely for abstract concepts like a playbook. | No |
| `tags` | A YAML list for cross-cutting filtering. | No |
| `timestamp` | ISO 8601 last-modified time. | No |

This exact file already exists in the repo at
[`examples/00_minimal_okf/datasets/web_traffic.md`](../examples/00_minimal_okf/datasets/web_traffic.md) —
compare your file to it.

## Verify it parses

You don't need this project's code to check that your frontmatter is
valid YAML — Python's standard library is enough:

```bash
python3 -c "
import re
text = open('hello.md').read()
front = text.split('---')[1]
import yaml
data = yaml.safe_load(front)
assert 'type' in data and data['type'], 'missing required type field'
print('OK:', data)
"
```

**Expected output:** `OK: {'type': 'Note'}` (or your own field values).
If it raises an `AssertionError` or a YAML parse error, re-check that:

1. Both `---` lines are present and exactly three dashes.
2. Indentation in the YAML block uses spaces, not tabs (YAML forbids
   tabs for indentation — this is the #1 hand-authoring mistake).
3. Any list uses either `tags: [a, b]` or a `-` per line, not a bare
   comma-separated string.

## Common beginner mistakes

- **Forgetting the closing `---`.** Without it, the whole file is
  treated as frontmatter with no body, or as invalid frontmatter
  entirely, depending on the parser.
- **Quoting when you don't need to, or not quoting when you do.** A
  `description` containing a colon (`Note: this is important`) must be
  quoted (`description: "Note: this is important"`) or YAML will
  misparse it as a nested mapping.
- **Treating `type` as a fixed enum.** It isn't. `type: Runbook` and
  `type: Playbook` are both legal; consumers are required to tolerate
  types they don't recognize (spec §9). Pick a vocabulary and be
  consistent *within your own bundle* — that consistency is what makes
  filtering and validation useful, not a central registry.
- **Skipping `title` and expecting a blank result.** Most consumers
  (including this repo's own tooling) derive a display title from the
  filename when `title` is absent — check [05 — Frontmatter & Fields](05-frontmatter-and-fields.md)
  before assuming a missing field breaks anything.

Next: [04 — Bundle Structure](04-bundle-structure.md), where this one
file becomes part of a real, multi-concept bundle.

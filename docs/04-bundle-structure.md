# 04 — Bundle Structure

## What a "bundle" is

A **knowledge bundle** is just a directory tree of markdown files. There
is no manifest file the spec requires, no database, nothing to
"initialize" — if you can make folders and text files, you can make a
bundle. The directory layout is entirely up to the producer; OKF does
not prescribe folder names or nesting rules (spec §3).

Walk the example bundle already committed in this repo:

```text
examples/00_minimal_okf/
├── index.md                        # bundle root index (see below)
├── log.md                          # bundle root changelog (see below)
├── datasets/
│   ├── index.md
│   └── web_traffic.md              # a concept
├── metrics/
│   └── weekly_active_users.md      # a concept
└── playbooks/
    └── first_response.md           # a concept
```

Open each file — there are only six, and by the end of this page you'll
understand exactly what every one of them is for.

## Concept IDs

A **concept** is one markdown file that isn't a reserved filename. Its
**concept ID** is its path inside the bundle with the `.md` suffix
removed (spec §2). So in the tree above:

| File | Concept ID |
|---|---|
| `datasets/web_traffic.md` | `datasets/web_traffic` |
| `metrics/weekly_active_users.md` | `metrics/weekly_active_users` |
| `playbooks/first_response.md` | `playbooks/first_response` |

Concept IDs matter because they're what cross-links and citations point
at — see [06 — Links, Index, Log, Citations](06-links-index-log-citations.md).

## The two reserved filenames

Exactly two filenames have spec-defined meaning at *any* level of the
tree, and **must not** be used for ordinary concepts (spec §3.1):

### `index.md` — a directory listing

Optional at any level, including the bundle root. Its job is
**progressive disclosure**: letting a reader (human or agent) see
*what's in a directory* before opening every file in it. It has **no
frontmatter** — just grouped markdown link lists:

```markdown
# Datasets

* [Website Traffic](web_traffic.md) - raw pageview and session events collected from the marketing site.
```

Compare to [`examples/00_minimal_okf/datasets/index.md`](../examples/00_minimal_okf/datasets/index.md).
A bundle-root `index.md` may additionally declare which spec version it
targets (spec §11):

```markdown
---
okf_version: "0.1"
---

# Team Wiki — Minimal OKF Bundle
...
```

This is the *only* place an `index.md` is allowed to have frontmatter.

### `log.md` — a changelog

Optional at any level. Records what changed and when, newest entry
first, with `YYYY-MM-DD` date headings (spec §7):

```markdown
# Directory Update Log

## 2026-06-15
* **Creation**: Added [Website Traffic](/datasets/web_traffic.md).
```

The leading bold word (`**Creation**`, `**Update**`, `**Deprecation**`)
is convention, not a fixed enum — write whatever's clearest.

## Organizing your own bundle

Because directory structure is unconstrained, the practical question is
"how *should* I organize one?" Two patterns cover most cases:

1. **Group by type** (what this repo's example, and its enterprise
   pipeline, both do): `datasets/`, `metrics/`, `apis/`, `playbooks/`.
   Easy to reason about, easy to write a per-type `index.md`.
2. **Group by domain**, with type expressed only in frontmatter:
   `sales/orders.md`, `sales/customers.md`, `sales/monthly_revenue.md`.
   Better when most questions are "show me everything about sales,"
   worse when most questions are "show me every metric regardless of
   domain."

Neither is more "correct" — pick whichever matches how people will
actually browse or query the bundle. You can always add `index.md`
files later to make either shape browsable.

## Checkpoint: build a bundle of your own

1. Make a new directory, `my_bundle/`.
2. Add two concept files under a subdirectory of your choice (reuse the
   pattern from [03](03-first-okf-document.md)).
3. Add an `index.md` in that subdirectory linking both.
4. Add a root `index.md` linking the subdirectory.

**How to verify success:** every `.md` file except your two `index.md`
files should parse with the one-liner from [doc 03](03-first-okf-document.md#verify-it-parses).
Your `index.md` files should have *no* frontmatter at all (except an
optional `okf_version` key on the root one) — if `yaml.safe_load` on an
`index.md` body returns something other than `None`/a plain string,
you've accidentally added frontmatter to a reserved file.

Next: [05 — Frontmatter & Fields](05-frontmatter-and-fields.md), where
we cover the gap between what the spec requires and what a real
production pipeline — like the one in this repo — usually demands on
top of it.

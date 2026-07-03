# 06 — Links, Index, Log, and Citations

Four small conventions turn a pile of markdown files into a navigable,
graph-shaped knowledge base. All four are demonstrated in
[`examples/00_minimal_okf/`](../examples/00_minimal_okf/) — open the
files alongside this page.

## Cross-linking concepts

OKF uses **standard markdown links**, nothing custom. Two forms exist
(spec §5):

### Absolute (bundle-relative) — recommended

Starts with `/`, resolved from the bundle root:

```markdown
See the [customers table](/tables/customers.md) for the join key.
```

This is recommended because the link stays correct even if the file
containing it moves to a different subdirectory later.

### Relative

Standard relative paths:

```markdown
See the [neighboring concept](./other.md).
```

### What a link means

A link from concept A to concept B asserts *some* relationship — the
specific kind (depends-on, joins-with, references) lives in the
surrounding prose, not in the link syntax itself (spec §5.3). A tool
building a graph view treats every link as a directed edge, full stop.

### Links are allowed to be broken

This is one of the spec's most beginner-surprising rules: **a link
pointing at a concept that doesn't exist yet is not invalid** (spec
§5.3, §9). It may simply represent knowledge someone hasn't written yet.
Spec-conformant consumers must tolerate this.

This repo's own validator is stricter here on purpose — see
[07 — Conformance & Validation](07-conformance-and-validation.md).
That's a deliberate repo-level choice, not something the spec itself
requires.

## `index.md` — progressive disclosure

Covered in [04 — Bundle Structure](04-bundle-structure.md#indexmd--a-directory-listing).
The core idea worth repeating here: an `index.md` lets a consumer (human
or agent) see "what exists in this directory" in one file, instead of
opening every concept just to find out. This matters enormously for
agents with limited context — an agent can read `index.md`, decide
which two or three concepts are relevant, and only then spend context
budget reading those specific files.

## `log.md` — chronological history

Also covered in [04](04-bundle-structure.md#logmd--a-changelog). The
practical use case: when a bundle changes over time (concepts added,
deprecated, corrected), `log.md` gives a human *or an agent* a fast way
to answer "what changed recently?" without diffing the whole bundle.

## Citations

When a concept's body makes a claim sourced from something external —
a doc page, a blog post, an internal wiki — that source **should** be
listed under a `# Citations` heading at the bottom, numbered (spec §8):

```markdown
# Citations

[1] [Active Users definition conventions](https://en.wikipedia.org/wiki/Active_users)
```

See [`examples/00_minimal_okf/metrics/weekly_active_users.md`](../examples/00_minimal_okf/metrics/weekly_active_users.md)
for a working example. Citation targets can be external URLs,
bundle-relative paths, or paths into a `references/` subdirectory that
mirrors external material as first-class concepts of their own — useful
when you want a citation to be as inspectable and versioned as the rest
of the bundle.

Citations are a **body convention**, not a frontmatter field — don't
confuse this with `sources` in [this repo's enterprise
profile](05-frontmatter-and-fields.md), which is a *frontmatter* list of
raw documents a concept was mechanically derived from. They solve
adjacent but different problems: `sources` is "where did this generated
file come from" (provenance); `# Citations` is "what backs up this
specific claim in the prose" (evidence).

## Checkpoint

Open [`examples/00_minimal_okf/datasets/web_traffic.md`](../examples/00_minimal_okf/datasets/web_traffic.md)
and [`examples/00_minimal_okf/metrics/weekly_active_users.md`](../examples/00_minimal_okf/metrics/weekly_active_users.md)
side by side. Trace the link from the metric to the dataset and back —
that round trip *is* the graph this repo's `graph-build` command
constructs automatically at larger scale (see
[08 — Real-World Workflows](08-real-world-workflows.md)).

Next: [07 — Conformance & Validation](07-conformance-and-validation.md).

# 01 — Why OKF Exists

## The problem, in plain English

Every team that has been running for more than a year accumulates
*knowledge that lives outside any database*: which API does what, why a
metric is defined the odd way it is, what to do when a pipeline breaks
at 3am, who owns which table. That knowledge ends up scattered across
wikis, Slack threads, code comments, a metadata catalog UI, and the
memory of whoever has been there longest.

Two separate audiences need that knowledge and are both currently
underserved:

1. **Humans**, who have to hunt across five tools to answer a question
   like "can I delete this table safely?"
2. **AI agents**, which need the same knowledge stuffed into their
   context window before they can answer a question grounded in facts
   instead of guessing. Every team building an agent today ends up
   solving *the same context-assembly problem* from scratch: how do I
   turn my org's scattered knowledge into something an LLM can read?

OKF's bet is that the fix for both audiences is the same fix, and it's
almost boringly simple: **write knowledge down as markdown files with a
small YAML header, organized in folders.** No new database. No new
query language. No SDK required to produce or consume it.

## Why not just use a normal metadata catalog?

Metadata catalogs (Dataplex, Unity Catalog, Collibra, and similar tools)
solve a related but different problem: they index *structured* metadata
about assets you already have (tables, pipelines, dashboards) behind an
API and a UI. That's valuable, but it has three properties that make it
a poor fit for agent context and cross-org knowledge sharing:

- **It's locked behind a service.** Reading it means calling an API or
  opening a UI — an LLM can't just read the bytes.
- **It's not diffable.** You can't `git diff` a change to see exactly
  what someone edited and why.
- **It's not portable.** Knowledge captured in one org's catalog
  instance doesn't travel to another org, another tool, or another
  team's agent without an export/import step.

OKF is not a replacement for those catalogs — a producer could export
*from* one into an OKF bundle. OKF's contribution is a common,
inspectable, portable *format* for the knowledge itself, independent of
whichever system stores or serves it.

## Why not just use "a wiki"?

You basically can — OKF formalizes a pattern that already existed
informally (teams keeping an "LLM wiki" of markdown files that they
paste into agent prompts). What OKF adds is **just enough structure to
make that pattern interoperable**:

- A required `type` field so any consumer can tell what kind of thing a
  document describes without reading the prose.
- A predictable way to declare "this file describes this many parent/child
  concepts, here's how to browse them" (`index.md`).
- A predictable way to record "here's what changed and when" (`log.md`).
- A convention for cross-linking documents so relationships (not just a
  folder hierarchy) are expressible.

Without those conventions, every team's "markdown wiki for agents" is
shaped slightly differently, and no tool can be built that works across
more than one of them. With them, a viewer, a validator, or a retrieval
system can be written once and pointed at *any* conformant bundle.

## What OKF deliberately does not do

The spec is explicit about its own boundaries (see
[SPEC.md §1, "Non-goals"](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md#1-motivation)):

- It does not define a fixed taxonomy of concept types — `type: API
  Endpoint` and `type: Metric` are conventions you pick, not values from
  a registry.
- It does not prescribe storage, serving, or query infrastructure —
  a bundle is just files; what serves them is up to you.
- It does not replace domain-specific schemas like Avro, Protobuf, or
  OpenAPI — a concept document can *reference* one of those, it doesn't
  reinvent it.

Keep this list in mind for [doc 05](05-frontmatter-and-fields.md): a lot
of what `enterprise-okf-ai` (this repo) adds on top of OKF exists
precisely to fill in choices the spec leaves open on purpose.

## Why this repo builds on OKF instead of inventing something else

`enterprise-okf-ai` needed a format for the knowledge bundle sitting
between raw enterprise documents and the retrieval/agent layer. OKF was
the natural choice because the same three properties that make it good
for cross-org sharing also make it good as *this pipeline's* internal
representation:

- Bundles are **git-diffable**, so a CI job can gate on "did this change
  introduce a broken link or a duplicate concept?" ([doc 07](07-conformance-and-validation.md)).
- Bundles are **plain text**, so the retrieval layer can build a BM25
  lexical index and a vector index from the same source of truth without
  a special connector.
- Bundles are **human-readable**, so when the agent cites a source, a
  person can open that exact file and verify the claim.

Next: [02 — Prerequisites](02-prerequisites.md).

# 10 — FAQ

**Is OKF a Google Cloud product I need a GCP account for?**
No. OKF is a file format specification — markdown plus YAML frontmatter.
Google Cloud's own reference agent (which produces bundles from
BigQuery) does use GCP, but the format itself needs nothing from Google
to read, write, or use. This repo's pipeline never calls a Google API.

**Is this repository built or endorsed by Google?**
No. `enterprise-okf-ai` is an independent, third-party project that
adopts OKF as its knowledge-bundle format. See
[00 — Overview](00-overview.md#where-okf-comes-from) for the official
Google sources this repo builds on.

**How mature is OKF, really?**
It's a **v0.1 draft**, announced by Google Cloud in June 2026. Treat it
as an early, actively-evolving specification, not an established
industry standard with a large existing tool ecosystem — this repo
doesn't claim otherwise, and neither should you when describing it to
others. Check the [official spec](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
for the current version.

**Is `type` really the only required frontmatter field?**
Yes, per the spec (see [03](03-first-okf-document.md) for a working
minimal example). This repo's own pipeline requires eight more fields
in the bundles *it* generates, but that's a repo-specific enterprise
convention, not a spec requirement — full breakdown in
[05 — Frontmatter & Fields](05-frontmatter-and-fields.md).

**What happens if I omit `title`?**
Consumers are expected to derive a display title from the filename
(spec §4.1). This repo's own tooling does this in several places (e.g.
the agent's lexical index falls back to the concept ID).

**Do OKF bundles have to be public?**
No — nothing about the format implies public distribution. A bundle is
just a directory; keep it in a private git repo, a private tarball, or
an internal filesystem mount, same as any other internal documentation.

**Does anything in this repo call an external AI API by default?**
No. The default configuration uses a deterministic, local embedding
fallback and runs the agent with `llm=None` (rule-based evidence
composition). Nothing reaches the network unless you explicitly
configure a real LLM/embedding provider — see
[11 — Next Steps](11-next-steps.md) and
[02 — Prerequisites](02-prerequisites.md#what-you-do-not-need).

**Can I plug in a real LLM (OpenAI, Gemini, a local Ollama model) instead of the rule-based agent?**
Yes — `EnterpriseAssistant` and `AgentOrchestrator.from_okf(...)` both
accept an `llm` argument; passing an object with an `.invoke(prompt)`
method (LangChain's chat model interface) is enough — see
[`src/agent/assistant.py`](../src/agent/assistant.py) and
[11 — Next Steps](11-next-steps.md) for a concrete pointer.

**Why markdown instead of JSON, YAML-only, or a database?**
Markdown lets prose and structure coexist in one file that's readable
without tooling and diffable in git. A pure-JSON or pure-YAML format
would be more rigidly structured but far less pleasant for the "long
description," "playbook steps," or "schema table" content that makes up
most of a real concept document. See
[01 — Why OKF](01-why-okf.md#why-not-just-use-a-normal-metadata-catalog)
for the fuller comparison against catalogs and wikis.

**What's `src/okfhub/`, and should I use it?**
It's an earlier, deprecated implementation kept in the repo for
backward compatibility. The README lists it explicitly under
Limitations. Don't build new work against it — everything in this
learning path uses `src/enterprise_okf_ai/`, the current package.

**I hand-wrote a bundle that passes OKF's spec conformance rules but fails this repo's `okf-validate`. Is my bundle wrong?**
No. It means your bundle is valid OKF but doesn't meet this repo's
additional, stricter enterprise profile. That's an intentional
distinction — re-read [05](05-frontmatter-and-fields.md) and
[07](07-conformance-and-validation.md) if this is confusing; it trips
up nearly everyone once, on purpose, so the distinction sticks.

**Where do I ask a question this FAQ didn't answer?**
Open an issue: <https://github.com/pypi-ahmad/google-okf-implementation/issues>.

Next: [11 — Next Steps](11-next-steps.md).

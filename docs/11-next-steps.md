# 11 — Next Steps

You've gone from "never heard of OKF" to hand-writing conformant
concept documents, understanding this repo's enterprise extensions, and
running the full ingest → validate → graph → index → retrieve → ask
pipeline. Here's where to go from here, roughly in order of effort.

## 1. Point the pipeline at your own documents

Swap `examples/enterprise_docs/` for a small folder of your own
markdown/PDF/DOCX/CSV files and re-run
[08 — Real-World Workflows](08-real-world-workflows.md) end to end.
Start small (5–10 documents) — it's much easier to sanity-check
`build-okf`'s concept typing and deduplication on a corpus you can read
in full.

## 2. Plug in a real LLM

The default agent runs with `llm=None` (rule-based evidence
composition — see [02](02-prerequisites.md) and [10](10-faq.md)).
`EnterpriseAssistant` accepts any object exposing `.invoke(prompt) ->
response` (LangChain's chat model interface). `langchain` itself is
already a project dependency, but the Ollama integration package is
not pinned in `pyproject.toml` — install it first with `uv add
langchain-ollama`. A minimal wiring, using Ollama running locally with
the model already named in `.env.example`:

```python
from langchain_ollama import ChatOllama  # requires: uv add langchain-ollama
from enterprise_okf_ai.agent import AgentOrchestrator
from enterprise_okf_ai.core.embeddings import deterministic_embedding

llm = ChatOllama(model="qwen3:8b", base_url="http://localhost:11434")
orchestrator = AgentOrchestrator.from_okf(
    okf_dir="okf_bundle",
    vector_dir="vector_db/chroma",
    embedding_fn=deterministic_embedding,
    llm=llm,
)
print(orchestrator.ask("Which API updates order status?").answer)
```

Compare the answer's *prose quality* to the rule-based version from
[08](08-real-world-workflows.md) — the grounding logic (evidence
selection, citations, abstention) doesn't change, only how the final
sentence is phrased.

## 3. Try the Streamlit UI and the FastAPI runtime

```bash
make run-ui    # interactive Streamlit app
make run-api   # POST /retrieval/search, /agent/ask, /agent/evaluate
```

The FastAPI layer is a thin wrapper over the same services the CLI
uses — reading [`src/enterprise_okf_ai/api/app.py`](../src/enterprise_okf_ai/api/app.py)
right after the CLI ([`src/enterprise_okf_ai/cli/main.py`](../src/enterprise_okf_ai/cli/main.py))
is a fast way to see how the same core logic gets exposed two ways.

## 4. Read the reference-lane docs

Now that you have the tutorial-lane mental model, the explanation-style
docs will make more sense on a fast read:

- [`docs/architecture.md`](architecture.md) — package layout and data flow.
- [`docs/retrieval.md`](retrieval.md) — router modes and score breakdown.
- [`docs/agent.md`](agent.md) — tool-calling contract and guardrails.
- [`docs/evaluation.md`](evaluation.md) — retrieval and agent benchmarks.

## 5. Work on a real, open limitation

This project documents its own gaps honestly — good places to
contribute or just to study as advanced exercises:

- **Abstention calibration** is weak (`abstain_accuracy = 0.5` on the
  current benchmark — see [`docs/evaluation.md`](evaluation.md)).
  Try tightening `_assess_support`'s thresholds in
  [`src/agent/assistant.py`](../src/agent/assistant.py) and see how the
  benchmark numbers move.
- **The strict validator's cycle detector** flags any mutual reference
  as an error (see [07](07-conformance-and-validation.md)) — a good,
  bounded exercise in reading `_check_cycles` in
  [`src/validators/okf_validator.py`](../src/validators/okf_validator.py)
  and considering what a less aggressive check would look like.
- **Reranking and section-aware retrieval scoring**, listed in the
  main [README](../README.md#future-improvements).

## 6. Go back to the source

- [OKF v0.1 spec](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) — re-read it now; it will read very differently than it did in [01](01-why-okf.md).
- [Official reference agent + viewer](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) — a *different* OKF producer/consumer than this repo, built around BigQuery. Comparing the two implementations is one of the fastest ways to internalize what's spec vs. what's implementation choice.
- [Google Cloud Blog announcement](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing) for the original motivating context.

## 7. If you get stuck again

[09 — Troubleshooting](09-troubleshooting.md) and
[10 — FAQ](10-faq.md) are written to be re-read, not just read once —
most confusion at this stage traces back to the spec-vs-extension
distinction from [05](05-frontmatter-and-fields.md).

# Agent Orchestration

## Purpose

The agent answers enterprise questions over OKF while minimizing hallucination risk through explicit tool use and evidence grounding.

## Tooling Surface

The assistant uses five tools:

1. `search_okf_documents` (local lexical OKF search)
2. `search_vector_db` (hybrid/vector retrieval)
3. `query_knowledge_graph` (relationship traversal)
4. `read_okf_file` (full-page evidence read)
5. `summarize_evidence` (grounded synthesis)

## Strategy Selection

- Structured dependency/ownership questions -> `graph_first`
- Broad conceptual questions -> `retrieval_first`

The selected strategy is returned in the response payload.

## Guardrails

Unsupported-answer safeguards include:

- minimum evidence hit threshold
- minimum top-score threshold
- lexical overlap checks between question and evidence
- explicit unsupported response with reason code

The agent does not force an answer when evidence is weak.

## Response Contract

Agent responses contain:

- `answer`
- `citations`
- `used_concepts`
- `tool_trace`
- `tool_calls`
- `evidence_summary`
- `confidence`
- `supported`
- `unsupported_reason`
- `strategy`

This supports observability, QA debugging, and production auditing.

## Runtime Interfaces

- CLI: `enterprise-okf-ai agent-ask`
- API: `POST /agent/ask`
- UI: Streamlit (`make run-ui`)

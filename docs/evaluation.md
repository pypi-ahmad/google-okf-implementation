# Evaluation Guide

## Scope

The project evaluates both retrieval quality and end-to-end agent quality.

## Retrieval Evaluation

Retrieval benchmarks focus on whether the right concepts are retrieved with enough rank quality.

Metrics:

- `recall@k`
- `MRR`
- `answer_support`

Primary code:

- `enterprise_okf_ai.retrieval.RetrievalEvaluator`
- `enterprise_okf_ai.retrieval.RetrievalBenchmarkSample`

## Agent Evaluation

Agent benchmarks validate grounded answering and abstention behavior.

Dataset:

- `examples/eval/agent_benchmark.json`

Metrics:

- `avg_concept_recall`
- `avg_answer_support`
- `abstain_accuracy`
- `supported_rate`

Primary code:

- `enterprise_okf_ai.agent.AgentEvaluationHarness`

## CLI

Run agent benchmark evaluation:

```bash
uv run enterprise-okf-ai agent-eval \
  --benchmark-path examples/eval/agent_benchmark.json \
  --top-k 8 \
  --output-json artifacts/agent_eval_report.json
```

## API

- `POST /agent/evaluate`

Request body:

```json
{
  "benchmark_path": "examples/eval/agent_benchmark.json",
  "top_k": 8
}
```

## Practical Guidance

- Keep benchmark questions stable across releases.
- Track summary metrics in CI and fail fast on major regressions.
- Include at least one abstain-required case to test hallucination safeguards.

import asyncio
from pathlib import Path

import orjson

from okfhub.evaluation import EvaluationService
from okfhub.models import AgentAnswer, EvaluationReport


class _DummyEngine:
    async def query(self, question: str, top_k: int | None = None) -> AgentAnswer:
        if "orders" in question.lower():
            return AgentAnswer(
                answer="Orders API updates customer orders.",
                citations=["apis/orders-api.md"],
                used_concepts=["apis/orders-api"],
                confidence=0.9,
                abstained=False,
            )
        return AgentAnswer(
            answer="No answer.",
            citations=[],
            used_concepts=[],
            confidence=0.1,
            abstained=True,
        )

    async def agent_query(self, question: str) -> AgentAnswer:
        return await self.query(question, top_k=None)


class _DummyOllama:
    async def chat_json(self, prompt: str) -> dict[str, object]:
        return {
            "faithfulness": 4,
            "helpfulness": 5,
            "completeness": 4,
            "verdict": "pass",
            "reason": "Grounded and complete.",
        }


def test_evaluation_service_computes_metrics_and_gate(tmp_path: Path) -> None:
    dataset_path = tmp_path / "gold_qa.json"
    dataset_path.write_bytes(
        orjson.dumps(
            [
                {
                    "example_id": "q1",
                    "question": "Which API updates customer orders?",
                    "expected_concepts": ["apis/orders-api"],
                    "reference_answer": "Orders API updates customer orders.",
                },
                {
                    "example_id": "q2",
                    "question": "Unknown question",
                    "expected_concepts": ["metrics/mau"],
                    "reference_answer": "N/A",
                },
            ]
        )
    )

    service = EvaluationService(engine=_DummyEngine(), ollama=_DummyOllama())
    report = asyncio.run(service.run(dataset_path=dataset_path, mode="query", top_k=8))

    assert isinstance(report, EvaluationReport)
    assert report.summary.total_examples == 2
    assert 0.0 <= report.summary.avg_recall_at_k <= 1.0
    assert 0.0 <= report.summary.avg_mrr <= 1.0
    assert report.summary.avg_faithfulness is not None

    # Compare report to itself: gate must pass with zero deltas.
    verdict = service.compare_reports(
        baseline=report,
        current=report,
        min_recall_delta=0.0,
        min_mrr_delta=0.0,
        min_faithfulness_delta=0.0,
    )
    assert verdict["passed"] is True

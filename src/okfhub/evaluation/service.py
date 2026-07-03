"""Evaluation service with retrieval metrics and optional LLM judge."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from loguru import logger

from okfhub.io import read_json
from okfhub.llm import OllamaClient
from okfhub.models import (
    AgentAnswer,
    EvaluationReport,
    EvaluationResultItem,
    EvaluationSummary,
    LLMJudgeScore,
    QAExample,
)
from okfhub.utils.okf import iso_now


class QueryEngine(Protocol):
    """Protocol for pipeline query surfaces used in evaluation."""

    async def query(self, question: str, top_k: int | None = None) -> AgentAnswer: ...

    async def agent_query(self, question: str) -> AgentAnswer: ...


class EvaluationService:
    """Run QA evaluation against a gold benchmark set."""

    def __init__(self, engine: QueryEngine, ollama: OllamaClient):
        self._engine = engine
        self._ollama = ollama

    async def run(self, dataset_path: Path, mode: str = "agent", top_k: int = 8) -> EvaluationReport:
        """Evaluate QA performance on a gold set.

        Args:
            dataset_path: Path to JSON gold question set.
            mode: `query` or `agent`.
            top_k: Retrieval depth for query mode.

        Returns:
            Evaluation report with metrics and per-item records.
        """

        examples = self._load_examples(dataset_path)
        items: list[EvaluationResultItem] = []

        for example in examples:
            answer = await self._run_one(example=example, mode=mode, top_k=top_k)
            recall = self._recall_at_k(example.expected_concepts, answer.used_concepts)
            reciprocal_rank = self._mrr(example.expected_concepts, answer.used_concepts)
            judge = await self._judge_answer(example, answer)

            items.append(
                EvaluationResultItem(
                    example_id=example.example_id,
                    question=example.question,
                    expected_concepts=example.expected_concepts,
                    retrieved_concepts=answer.used_concepts,
                    citations=answer.citations,
                    answer=answer.answer,
                    recall_at_k=recall,
                    reciprocal_rank=reciprocal_rank,
                    judge=judge,
                )
            )

        summary = self._build_summary(items)
        report = EvaluationReport(
            mode=mode,
            top_k=top_k,
            dataset_path=dataset_path.as_posix(),
            generated_at=iso_now(),
            summary=summary,
            items=items,
        )
        logger.info(
            "Evaluation complete: examples={} recall@k={:.3f} mrr={:.3f}",
            summary.total_examples,
            summary.avg_recall_at_k,
            summary.avg_mrr,
        )
        return report

    def compare_reports(
        self,
        baseline: EvaluationReport,
        current: EvaluationReport,
        min_recall_delta: float = -0.02,
        min_mrr_delta: float = -0.02,
        min_faithfulness_delta: float = -0.15,
    ) -> dict[str, object]:
        """Compare evaluation reports and return pass/fail regression gate."""

        recall_delta = current.summary.avg_recall_at_k - baseline.summary.avg_recall_at_k
        mrr_delta = current.summary.avg_mrr - baseline.summary.avg_mrr

        faithfulness_ok = True
        faithfulness_delta = None
        if (
            current.summary.avg_faithfulness is not None
            and baseline.summary.avg_faithfulness is not None
        ):
            faithfulness_delta = current.summary.avg_faithfulness - baseline.summary.avg_faithfulness
            faithfulness_ok = faithfulness_delta >= min_faithfulness_delta

        passed = (
            recall_delta >= min_recall_delta
            and mrr_delta >= min_mrr_delta
            and faithfulness_ok
        )

        checks = {
            "recall_delta": {
                "value": recall_delta,
                "threshold": min_recall_delta,
                "passed": recall_delta >= min_recall_delta,
            },
            "mrr_delta": {
                "value": mrr_delta,
                "threshold": min_mrr_delta,
                "passed": mrr_delta >= min_mrr_delta,
            },
            "faithfulness_delta": {
                "value": faithfulness_delta,
                "threshold": min_faithfulness_delta,
                "passed": faithfulness_ok,
                "skipped": faithfulness_delta is None,
            },
        }

        return {
            "passed": passed,
            "baseline_generated_at": baseline.generated_at,
            "current_generated_at": current.generated_at,
            "checks": checks,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _load_examples(self, dataset_path: Path) -> list[QAExample]:
        payload = read_json(dataset_path)
        if not isinstance(payload, list):
            raise ValueError("Evaluation dataset must be a JSON list")

        return [QAExample.model_validate(item) for item in payload]

    async def _run_one(self, example: QAExample, mode: str, top_k: int) -> AgentAnswer:
        if mode == "query":
            return await self._engine.query(question=example.question, top_k=top_k)
        if mode == "agent":
            return await self._engine.agent_query(example.question)

        raise ValueError("mode must be one of: query, agent")

    async def _judge_answer(self, example: QAExample, answer: AgentAnswer) -> LLMJudgeScore | None:
        prompt = (
            "Score the answer on a 1-5 scale for faithfulness, helpfulness, and completeness. "
            "Use reference answer and expected concepts when available. Return JSON keys: "
            "faithfulness, helpfulness, completeness, verdict, reason. verdict must be pass or fail.\n\n"
            f"Question: {example.question}\n"
            f"Expected concepts: {example.expected_concepts}\n"
            f"Reference answer: {example.reference_answer or ''}\n"
            f"Model answer: {answer.answer}\n"
            f"Citations: {answer.citations}"
        )

        try:
            raw = await self._ollama.chat_json(prompt)
            if not isinstance(raw, dict):
                return None
            return LLMJudgeScore(
                faithfulness=self._to_optional_float(raw.get("faithfulness")),
                helpfulness=self._to_optional_float(raw.get("helpfulness")),
                completeness=self._to_optional_float(raw.get("completeness")),
                verdict=str(raw.get("verdict", "unknown")).lower(),
                reason=str(raw.get("reason", "")),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM judge unavailable: {}", exc)
            return None

    def _build_summary(self, items: list[EvaluationResultItem]) -> EvaluationSummary:
        count = max(1, len(items))
        avg_recall = sum(item.recall_at_k for item in items) / count
        avg_mrr = sum(item.reciprocal_rank for item in items) / count
        citation_coverage = sum(1 for item in items if item.citations) / count

        judge_items = [item.judge for item in items if item.judge is not None]
        if judge_items:
            faithfulness_values = [score.faithfulness for score in judge_items if score.faithfulness is not None]
            helpfulness_values = [score.helpfulness for score in judge_items if score.helpfulness is not None]
            completeness_values = [score.completeness for score in judge_items if score.completeness is not None]
            pass_rate = sum(1 for score in judge_items if score.verdict == "pass") / len(judge_items)
        else:
            faithfulness_values = []
            helpfulness_values = []
            completeness_values = []
            pass_rate = None

        def _avg(values: list[float]) -> float | None:
            return (sum(values) / len(values)) if values else None

        return EvaluationSummary(
            total_examples=len(items),
            avg_recall_at_k=avg_recall,
            avg_mrr=avg_mrr,
            citation_coverage=citation_coverage,
            avg_faithfulness=_avg(faithfulness_values),
            avg_helpfulness=_avg(helpfulness_values),
            avg_completeness=_avg(completeness_values),
            pass_rate=pass_rate,
        )

    def _recall_at_k(self, expected: list[str], retrieved: list[str]) -> float:
        if not expected:
            return 1.0
        expected_set = {item.strip().lower() for item in expected if item.strip()}
        retrieved_set = {item.strip().lower() for item in retrieved if item.strip()}
        if not expected_set:
            return 1.0
        overlap = expected_set.intersection(retrieved_set)
        return len(overlap) / len(expected_set)

    def _mrr(self, expected: list[str], retrieved: list[str]) -> float:
        expected_set = {item.strip().lower() for item in expected if item.strip()}
        if not expected_set:
            return 1.0

        for idx, concept in enumerate(retrieved, start=1):
            if concept.strip().lower() in expected_set:
                return 1.0 / idx
        return 0.0

    def _to_optional_float(self, value: object) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

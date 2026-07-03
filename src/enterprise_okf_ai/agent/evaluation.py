"""Evaluation harness for agentic OKF question answering."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import orjson

from enterprise_okf_ai.agent.orchestrator import AgentOrchestrator


@dataclass(slots=True)
class AgentBenchmarkCase:
    """Single benchmark case for agent QA evaluation."""

    case_id: str
    question: str
    expected_concepts: list[str]
    support_terms: list[str]
    should_abstain: bool = False


@dataclass(slots=True)
class AgentEvaluationItem:
    """Per-case evaluation output."""

    case_id: str
    question: str
    expected_concepts: list[str]
    used_concepts: list[str]
    citations: list[str]
    supported: bool
    confidence: float
    concept_recall: float
    answer_support: float
    abstain_correct: bool


@dataclass(slots=True)
class AgentEvaluationSummary:
    """Aggregate evaluation metrics."""

    total_cases: int
    avg_concept_recall: float
    avg_answer_support: float
    abstain_accuracy: float
    supported_rate: float


@dataclass(slots=True)
class AgentEvaluationReport:
    """Evaluation report for benchmark run."""

    summary: AgentEvaluationSummary
    items: list[AgentEvaluationItem]

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to a JSON-ready dictionary."""

        return {
            "summary": asdict(self.summary),
            "items": [asdict(item) for item in self.items],
        }


class AgentEvaluationHarness:
    """Benchmark harness for enterprise agent behavior."""

    def __init__(self, orchestrator: AgentOrchestrator):
        self._orchestrator = orchestrator

    def run(self, cases: list[AgentBenchmarkCase], top_k: int = 8) -> AgentEvaluationReport:
        """Run benchmark questions and compute aggregate metrics."""

        items: list[AgentEvaluationItem] = []

        for case in cases:
            response = self._orchestrator.ask(question=case.question, top_k=top_k)

            concept_recall = self._concept_recall(case.expected_concepts, response.used_concepts)
            answer_support = self._answer_support(case.support_terms, response.answer, response.evidence_summary)
            abstain_correct = (not response.supported) if case.should_abstain else response.supported

            items.append(
                AgentEvaluationItem(
                    case_id=case.case_id,
                    question=case.question,
                    expected_concepts=case.expected_concepts,
                    used_concepts=response.used_concepts,
                    citations=response.citations,
                    supported=response.supported,
                    confidence=response.confidence,
                    concept_recall=concept_recall,
                    answer_support=answer_support,
                    abstain_correct=abstain_correct,
                )
            )

        return AgentEvaluationReport(summary=self._summarize(items), items=items)

    def load_cases(self, path: str | Path) -> list[AgentBenchmarkCase]:
        """Load benchmark cases from JSON file."""

        payload = orjson.loads(Path(path).read_bytes())
        if not isinstance(payload, list):
            raise ValueError("Benchmark payload must be a JSON list")

        cases: list[AgentBenchmarkCase] = []
        for idx, item in enumerate(payload):
            if not isinstance(item, dict):
                raise ValueError(f"Benchmark case at index {idx} is not an object")

            case_id = str(item.get("case_id", f"case-{idx+1}")).strip()
            question = str(item.get("question", "")).strip()
            if not question:
                raise ValueError(f"Benchmark case {case_id} has empty question")

            expected_concepts = item.get("expected_concepts", [])
            support_terms = item.get("support_terms", [])
            should_abstain = bool(item.get("should_abstain", False))

            if not isinstance(expected_concepts, list):
                raise ValueError(f"Benchmark case {case_id} expected_concepts must be a list")
            if not isinstance(support_terms, list):
                raise ValueError(f"Benchmark case {case_id} support_terms must be a list")

            cases.append(
                AgentBenchmarkCase(
                    case_id=case_id,
                    question=question,
                    expected_concepts=[str(concept) for concept in expected_concepts],
                    support_terms=[str(term) for term in support_terms],
                    should_abstain=should_abstain,
                )
            )

        return cases

    def _summarize(self, items: list[AgentEvaluationItem]) -> AgentEvaluationSummary:
        count = max(1, len(items))
        return AgentEvaluationSummary(
            total_cases=len(items),
            avg_concept_recall=sum(item.concept_recall for item in items) / count,
            avg_answer_support=sum(item.answer_support for item in items) / count,
            abstain_accuracy=sum(1 for item in items if item.abstain_correct) / count,
            supported_rate=sum(1 for item in items if item.supported) / count,
        )

    def _concept_recall(self, expected: list[str], used: list[str]) -> float:
        expected_set = {item.strip().lower() for item in expected if item.strip()}
        if not expected_set:
            return 1.0
        used_set = {item.strip().lower() for item in used if item.strip()}
        if not used_set:
            return 0.0
        overlap = expected_set.intersection(used_set)
        return len(overlap) / len(expected_set)

    def _answer_support(self, support_terms: list[str], answer: str, evidence_summary: str) -> float:
        if not support_terms:
            return 1.0

        text = f"{answer}\n{evidence_summary}".lower()
        total = 0
        hits = 0
        for phrase in support_terms:
            cleaned = phrase.strip().lower()
            if not cleaned:
                continue
            total += 1
            if all(token in text for token in cleaned.split()):
                hits += 1
        if total == 0:
            return 1.0
        return hits / total

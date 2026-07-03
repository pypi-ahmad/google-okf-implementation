"""Evaluation utilities for hybrid retrieval quality."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from rag.retriever import RetrievalResult, SearchRoute


class RetrievalEngine(Protocol):
    """Protocol for retrieval engines that expose `search`."""

    def search(
        self,
        query: str,
        top_k: int = 8,
        use_graph_expansion: bool = True,
        route: SearchRoute = "auto",
    ) -> list[RetrievalResult]:
        """Return ranked retrieval hits for a query."""
        ...


@dataclass(slots=True)
class RetrievalBenchmarkSample:
    """Single gold sample used for retrieval evaluation."""

    query: str
    expected_concept_ids: list[str]
    support_terms: list[str] = field(default_factory=list)
    route: SearchRoute = "auto"


@dataclass(slots=True)
class RetrievalEvaluationItem:
    """Per-query retrieval evaluation record."""

    query: str
    route: str
    expected_concept_ids: list[str]
    retrieved_concept_ids: list[str]
    recall_at_k: float
    reciprocal_rank: float
    answer_support: float
    top_score: float | None


@dataclass(slots=True)
class RetrievalEvaluationSummary:
    """Aggregate retrieval evaluation summary."""

    total_queries: int
    avg_recall_at_k: float
    avg_mrr: float
    avg_answer_support: float


@dataclass(slots=True)
class RetrievalEvaluationReport:
    """Full retrieval evaluation output."""

    summary: RetrievalEvaluationSummary
    items: list[RetrievalEvaluationItem]


def recall_at_k(expected: list[str], retrieved: list[str], k: int) -> float:
    """Compute recall@k over concept IDs."""

    expected_set = {item.strip().lower() for item in expected if item.strip()}
    if not expected_set:
        return 1.0

    retrieved_set = {
        item.strip().lower()
        for item in retrieved[: max(k, 0)]
        if item.strip()
    }
    if not retrieved_set:
        return 0.0

    overlap = expected_set.intersection(retrieved_set)
    return len(overlap) / len(expected_set)


def mean_reciprocal_rank(expected: list[str], retrieved: list[str]) -> float:
    """Compute reciprocal rank for the first relevant retrieved concept."""

    expected_set = {item.strip().lower() for item in expected if item.strip()}
    if not expected_set:
        return 1.0

    for index, concept_id in enumerate(retrieved, start=1):
        if concept_id.strip().lower() in expected_set:
            return 1.0 / index
    return 0.0


def answer_support_score(
    expected: list[str],
    retrieved_results: list[RetrievalResult],
    support_terms: list[str] | None = None,
) -> float:
    """Estimate how well retrieved evidence can support an answer.

    The score blends:
    - concept support (coverage of expected concept IDs),
    - lexical support (coverage of expected support phrases in retrieved snippets/titles).
    """

    support_terms = support_terms or []
    retrieved_ids = [result.concept_id for result in retrieved_results]
    concept_support = recall_at_k(expected, retrieved_ids, k=len(retrieved_ids))

    if not support_terms:
        return concept_support

    evidence_parts: list[str] = []
    for result in retrieved_results:
        evidence_parts.extend(
            [
                result.title,
                result.snippet,
                result.metadata.get("resource", ""),
                result.metadata.get("tags", ""),
            ]
        )
    evidence_text = " ".join(evidence_parts).lower()
    phrase_hits = 0
    for phrase in support_terms:
        cleaned = phrase.strip().lower()
        if not cleaned:
            continue
        phrase_tokens = cleaned.split()
        if phrase_tokens and all(token in evidence_text for token in phrase_tokens):
            phrase_hits += 1

    lexical_support = phrase_hits / max(1, len([item for item in support_terms if item.strip()]))

    if expected:
        return (concept_support + lexical_support) / 2.0
    return lexical_support


class RetrievalEvaluator:
    """Run benchmark evaluation over a retrieval engine."""

    def __init__(self, engine: RetrievalEngine):
        self._engine = engine

    def evaluate(
        self,
        samples: list[RetrievalBenchmarkSample],
        top_k: int = 8,
        use_graph_expansion: bool = True,
    ) -> RetrievalEvaluationReport:
        """Evaluate retrieval engine with recall@k, MRR, and answer support."""

        items: list[RetrievalEvaluationItem] = []
        for sample in samples:
            results = self._engine.search(
                query=sample.query,
                top_k=top_k,
                use_graph_expansion=use_graph_expansion,
                route=sample.route,
            )
            retrieved_ids = [result.concept_id for result in results]
            items.append(
                RetrievalEvaluationItem(
                    query=sample.query,
                    route=sample.route,
                    expected_concept_ids=sample.expected_concept_ids,
                    retrieved_concept_ids=retrieved_ids,
                    recall_at_k=recall_at_k(sample.expected_concept_ids, retrieved_ids, k=top_k),
                    reciprocal_rank=mean_reciprocal_rank(sample.expected_concept_ids, retrieved_ids),
                    answer_support=answer_support_score(
                        expected=sample.expected_concept_ids,
                        retrieved_results=results,
                        support_terms=sample.support_terms,
                    ),
                    top_score=results[0].score if results else None,
                )
            )

        summary = self._summarize(items)
        return RetrievalEvaluationReport(summary=summary, items=items)

    def _summarize(self, items: list[RetrievalEvaluationItem]) -> RetrievalEvaluationSummary:
        count = max(1, len(items))
        return RetrievalEvaluationSummary(
            total_queries=len(items),
            avg_recall_at_k=sum(item.recall_at_k for item in items) / count,
            avg_mrr=sum(item.reciprocal_rank for item in items) / count,
            avg_answer_support=sum(item.answer_support for item in items) / count,
        )

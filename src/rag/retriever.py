"""Hybrid retrieval router over OKF markdown bundles.

This module provides:
- semantic retrieval through a vector store,
- lexical retrieval through BM25,
- graph traversal retrieval over a NetworkX knowledge graph,
- an auto-router that selects vector/keyword/graph/hybrid strategies,
- ranked hits with score breakdown and explanation traces.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import networkx as nx
import yaml
from rank_bm25 import BM25Okapi

from vector_db.indexer import ChromaVectorStore

logger = logging.getLogger(__name__)

SearchRoute = Literal["auto", "vector", "keyword", "graph", "hybrid"]

# OKF reserves `index.md` and `log.md`. `README.md` is a concept document under the spec.
RESERVED_FILES = {"index.md", "log.md"}
TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")

GRAPH_INTENT_TERMS = {
    "depend",
    "depends",
    "dependency",
    "dependencies",
    "upstream",
    "downstream",
    "owner",
    "owned",
    "uses",
    "used",
    "lineage",
    "impact",
    "linked",
    "relationship",
    "references",
    "reference",
}

KEYWORD_INTENT_TERMS = {
    "schema",
    "column",
    "field",
    "table",
    "resource",
    "slug",
    "id",
    "path",
    "endpoint",
    "runbook",
    "playbook",
    "sql",
}

VECTOR_INTENT_TERMS = {
    "explain",
    "overview",
    "describe",
    "summary",
    "context",
    "purpose",
    "why",
    "how",
}

TYPE_HINTS: dict[str, set[str]] = {
    "api": {"api", "endpoint", "service", "request", "response"},
    "dataset": {"dataset", "warehouse", "source", "lineage"},
    "table": {"table", "schema", "column", "ddl"},
    "metric": {"metric", "kpi", "formula", "calculate", "definition"},
    "playbook": {"playbook", "runbook", "incident", "oncall", "escalation"},
    "glossary": {"glossary", "term", "acronym", "definition"},
}

BASE_ROUTE_WEIGHTS: dict[str, dict[str, float]] = {
    "vector": {"semantic": 0.82, "keyword": 0.08, "graph": 0.05, "structured": 0.05},
    "keyword": {"semantic": 0.08, "keyword": 0.82, "graph": 0.05, "structured": 0.05},
    "graph": {"semantic": 0.15, "keyword": 0.2, "graph": 0.55, "structured": 0.1},
    "hybrid": {"semantic": 0.42, "keyword": 0.33, "graph": 0.17, "structured": 0.08},
}


@dataclass(slots=True)
class RetrievalResult:
    """Single ranked retrieval result with scoring trace."""

    concept_id: str
    path: str
    title: str
    concept_type: str
    score: float
    source: str
    snippet: str
    metadata: dict[str, str]
    score_breakdown: dict[str, float] = field(default_factory=dict)
    explanation_trace: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DocumentRecord:
    """Internal OKF document representation for retrieval."""

    concept_id: str
    path: Path
    frontmatter: dict[str, Any]
    body: str
    raw_text: str


@dataclass(slots=True)
class SearchResponse:
    """Structured response for search with router-level traces."""

    query: str
    route: str
    top_k: int
    router_trace: list[str]
    results: list[RetrievalResult]


@dataclass(slots=True)
class RouteDecision:
    """Router decision payload."""

    route: str
    reasons: list[str]


def graph_traversal_retrieval(
    initial_results: list[RetrievalResult],
    graph: nx.DiGraph,
    lookup: dict[str, DocumentRecord],
    depth: int = 2,
) -> list[RetrievalResult]:
    """Expand API-centric retrieval results with linked dataset/metric/table docs."""

    expanded: list[RetrievalResult] = list(initial_results)
    seen_ids = {result.concept_id for result in initial_results}

    for result in initial_results:
        if result.concept_type.lower() != "api":
            continue

        if result.concept_id not in graph:
            continue

        frontier = {result.concept_id}
        visited = {result.concept_id}

        for level in range(1, depth + 1):
            next_frontier: set[str] = set()
            for node in frontier:
                successors = set(graph.successors(node))
                predecessors = set(graph.predecessors(node))
                for neighbor in successors.union(predecessors):
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)
                    next_frontier.add(neighbor)

                    node_type = str(graph.nodes[neighbor].get("type", "")).lower()
                    if node_type not in {"dataset", "metric", "table"}:
                        continue
                    if neighbor in seen_ids:
                        continue

                    record = lookup.get(neighbor)
                    if record is None:
                        continue

                    related_score = max(0.2, result.score * (0.75**level))
                    expanded.append(
                        RetrievalResult(
                            concept_id=neighbor,
                            path=record.path.as_posix(),
                            title=str(record.frontmatter.get("title", neighbor)),
                            concept_type=node_type,
                            score=related_score,
                            source="graph_traversal",
                            snippet=record.body[:320],
                            metadata={
                                "type": node_type,
                                "title": str(record.frontmatter.get("title", neighbor)),
                                "resource": str(record.frontmatter.get("resource", "")),
                                "tags": ",".join(str(tag) for tag in record.frontmatter.get("tags", [])),
                            },
                            score_breakdown={
                                "semantic": 0.0,
                                "keyword": 0.0,
                                "graph": 1.0,
                                "structured": 0.0,
                                "final": float(related_score),
                            },
                            explanation_trace=[
                                "route=graph_traversal",
                                f"expanded_from={result.concept_id}",
                                f"depth={level}",
                            ],
                        )
                    )
                    seen_ids.add(neighbor)
            frontier = next_frontier
            if not frontier:
                break

    expanded.sort(key=lambda item: item.score, reverse=True)
    return expanded


class HybridSearchRouter:
    """Hybrid retrieval router using semantic, lexical, and graph signals.

    Example:
        >>> router = HybridSearchRouter(okf_dir="okf_bundle", vector_store=store, embedding_fn=my_embed_fn)
        >>> response = router.search_with_trace("Which API updates customer orders?")
        >>> response.route
        'hybrid'
    """

    def __init__(
        self,
        okf_dir: str | Path,
        vector_store: ChromaVectorStore,
        embedding_fn: Any,
        graph: nx.DiGraph | None = None,
        semantic_weight: float = 0.6,
        bm25_weight: float = 0.4,
    ):
        self.okf_dir = Path(okf_dir)
        self.vector_store = vector_store
        self.embedding_fn = embedding_fn
        self.graph = graph
        self.semantic_weight = semantic_weight
        self.bm25_weight = bm25_weight

        self._documents = self._load_documents(self.okf_dir)
        self._lookup = {doc.concept_id: doc for doc in self._documents}

        self._tokenized_docs = [self._tokenize(doc.raw_text) for doc in self._documents]
        self._bm25 = BM25Okapi(self._tokenized_docs) if self._tokenized_docs else None

    def search(
        self,
        query: str,
        top_k: int = 8,
        use_graph_expansion: bool = True,
        route: SearchRoute = "auto",
    ) -> list[RetrievalResult]:
        """Run retrieval and return ranked result hits."""

        response = self.search_with_trace(
            query=query,
            top_k=top_k,
            use_graph_expansion=use_graph_expansion,
            route=route,
        )
        return response.results

    def search_with_trace(
        self,
        query: str,
        top_k: int = 8,
        use_graph_expansion: bool = True,
        route: SearchRoute = "auto",
    ) -> SearchResponse:
        """Run retrieval and return router + scoring traces."""

        cleaned_query = query.strip()
        if not cleaned_query:
            return SearchResponse(
                query=query,
                route="hybrid",
                top_k=top_k,
                router_trace=["empty query provided"],
                results=[],
            )

        if not self._documents:
            return SearchResponse(
                query=query,
                route="hybrid",
                top_k=top_k,
                router_trace=["no OKF documents available"],
                results=[],
            )

        decision = self._decide_route(cleaned_query, route)
        selected_route = decision.route
        router_trace = list(decision.reasons)

        semantic_enabled = selected_route in {"vector", "graph", "hybrid"}
        keyword_enabled = selected_route in {"keyword", "graph", "hybrid"}
        graph_enabled = selected_route in {"graph", "hybrid", "vector", "keyword"} and self.graph is not None

        semantic_scores = (
            self._semantic_scores(query=cleaned_query, top_k=max(top_k * 3, 16))
            if semantic_enabled
            else {}
        )
        keyword_scores = self._bm25_scores(query=cleaned_query) if keyword_enabled else {}
        graph_scores = (
            self._graph_scores(
                query=cleaned_query,
                semantic_scores=semantic_scores,
                keyword_scores=keyword_scores,
                top_k=max(top_k * 3, 16),
            )
            if graph_enabled
            else {}
        )
        structured_scores = self._structured_scores(cleaned_query)

        weights = self._effective_weights(
            selected_route,
            has_semantic=bool(semantic_scores),
            has_keyword=bool(keyword_scores),
            has_graph=bool(graph_scores),
            has_structured=bool(structured_scores),
        )
        router_trace.append(
            "weights="
            + ",".join(f"{key}:{value:.2f}" for key, value in weights.items())
        )
        if graph_scores:
            graph_seeds = ", ".join(self._graph_seed_ids(cleaned_query, semantic_scores, keyword_scores, limit=4))
            if graph_seeds:
                router_trace.append(f"graph_seeds={graph_seeds}")

        candidate_ids: set[str] = set()
        candidate_ids.update(semantic_scores.keys())
        candidate_ids.update(keyword_scores.keys())
        candidate_ids.update(graph_scores.keys())
        candidate_ids.update(structured_scores.keys())
        if not candidate_ids:
            return SearchResponse(
                query=query,
                route=selected_route,
                top_k=top_k,
                router_trace=router_trace + ["no retrieval candidates produced"],
                results=[],
            )

        scored: list[RetrievalResult] = []
        for concept_id in candidate_ids:
            if concept_id not in self._lookup:
                continue

            semantic_score = semantic_scores.get(concept_id, 0.0)
            keyword_score = keyword_scores.get(concept_id, 0.0)
            graph_score = graph_scores.get(concept_id, 0.0)
            structured_score = structured_scores.get(concept_id, 0.0)

            final_score = (
                weights["semantic"] * semantic_score
                + weights["keyword"] * keyword_score
                + weights["graph"] * graph_score
                + weights["structured"] * structured_score
            )

            trace = [f"route={selected_route}"]
            if semantic_score > 0:
                trace.append(f"semantic={semantic_score:.3f}*{weights['semantic']:.2f}")
            if keyword_score > 0:
                trace.append(f"keyword={keyword_score:.3f}*{weights['keyword']:.2f}")
            if graph_score > 0:
                trace.append(f"graph={graph_score:.3f}*{weights['graph']:.2f}")
            if structured_score > 0:
                trace.append(f"structured={structured_score:.3f}*{weights['structured']:.2f}")

            scored.append(
                self._to_result(
                    concept_id=concept_id,
                    score=final_score,
                    source=f"{selected_route}_route",
                    score_breakdown={
                        "semantic": float(semantic_score),
                        "keyword": float(keyword_score),
                        "graph": float(graph_score),
                        "structured": float(structured_score),
                        "final": float(final_score),
                    },
                    explanation_trace=trace,
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        ranked = scored[:top_k]

        if use_graph_expansion and self.graph is not None:
            ranked = graph_traversal_retrieval(
                initial_results=ranked,
                graph=self.graph,
                lookup=self._lookup,
                depth=2,
            )[:top_k]

        return SearchResponse(
            query=query,
            route=selected_route,
            top_k=top_k,
            router_trace=router_trace,
            results=ranked,
        )

    def _decide_route(self, query: str, requested_route: SearchRoute) -> RouteDecision:
        if requested_route != "auto":
            return RouteDecision(
                route=requested_route,
                reasons=[f"route explicitly requested: {requested_route}"],
            )

        query_lower = query.lower()
        query_tokens = set(self._tokenize(query))

        has_graph_signal = any(term in query_lower for term in GRAPH_INTENT_TERMS)
        has_keyword_signal = any(term in query_tokens for term in KEYWORD_INTENT_TERMS) or any(
            marker in query for marker in ("/", ":", "_", ".")
        )
        has_vector_signal = any(term in query_tokens for term in VECTOR_INTENT_TERMS)

        if self.graph is not None and has_graph_signal:
            return RouteDecision(
                route="graph",
                reasons=["auto route selected graph traversal due to relationship cues"],
            )

        if has_keyword_signal and not has_vector_signal:
            return RouteDecision(
                route="keyword",
                reasons=["auto route selected keyword retrieval due to schema/identifier cues"],
            )

        if has_vector_signal and not has_keyword_signal:
            return RouteDecision(
                route="vector",
                reasons=["auto route selected vector retrieval due to semantic/explainer cues"],
            )

        return RouteDecision(
            route="hybrid",
            reasons=["auto route selected hybrid ensemble due to mixed query intent"],
        )

    def _semantic_scores(self, query: str, top_k: int) -> dict[str, float]:
        if not self._documents:
            return {}

        embedding = self.embedding_fn([query])[0]
        response = self.vector_store.query(embedding=embedding, top_k=top_k)

        ids = response.get("ids", [[]])[0]
        distances = response.get("distances", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]

        scores: dict[str, float] = {}
        if not ids:
            return scores

        for raw_id, distance, metadata in zip(ids, distances, metadatas, strict=False):
            concept_id = self._concept_id_from_vector_hit(raw_id=raw_id, metadata=metadata)
            similarity = 1.0 / (1.0 + float(distance))
            current = scores.get(concept_id, 0.0)
            scores[concept_id] = max(current, similarity)

        return self._normalize(scores)

    def _bm25_scores(self, query: str) -> dict[str, float]:
        if self._bm25 is None or not self._documents:
            return {}

        query_tokens = self._tokenize(query)
        raw_scores = self._bm25.get_scores(query_tokens)
        by_id = {
            self._documents[index].concept_id: float(score)
            for index, score in enumerate(raw_scores)
        }
        return self._normalize(by_id)

    def _graph_scores(
        self,
        query: str,
        semantic_scores: dict[str, float],
        keyword_scores: dict[str, float],
        top_k: int,
    ) -> dict[str, float]:
        if self.graph is None:
            return {}

        seed_ids = self._graph_seed_ids(query, semantic_scores, keyword_scores, limit=max(3, min(8, top_k // 2)))
        if not seed_ids:
            return {}

        scores: dict[str, float] = {}
        depth = 2 if self._is_relationship_query(query) else 1

        for rank, seed in enumerate(seed_ids):
            if seed not in self.graph:
                continue

            seed_base = max(0.4, 1.0 - (rank * 0.12))
            scores[seed] = max(scores.get(seed, 0.0), seed_base)

            frontier = {seed}
            visited = {seed}

            for level in range(1, depth + 1):
                next_frontier: set[str] = set()
                for node in frontier:
                    outgoing = set(self.graph.successors(node))
                    incoming = set(self.graph.predecessors(node))
                    for neighbor in outgoing.union(incoming):
                        if neighbor in visited:
                            continue
                        visited.add(neighbor)
                        next_frontier.add(neighbor)
                        propagated = seed_base * (0.75**level)
                        scores[neighbor] = max(scores.get(neighbor, 0.0), propagated)

                frontier = next_frontier
                if not frontier:
                    break

        return self._normalize(scores)

    def _graph_seed_ids(
        self,
        query: str,
        semantic_scores: dict[str, float],
        keyword_scores: dict[str, float],
        limit: int,
    ) -> list[str]:
        query_tokens = set(self._tokenize(query))
        seed_scores: dict[str, float] = defaultdict(float)

        for concept_id, score in semantic_scores.items():
            seed_scores[concept_id] += score * 0.55
        for concept_id, score in keyword_scores.items():
            seed_scores[concept_id] += score * 0.65

        for doc in self._documents:
            tags = doc.frontmatter.get("tags", [])
            if not isinstance(tags, list):
                tags = []
            fields = " ".join(
                [
                    str(doc.frontmatter.get("title", "")),
                    str(doc.frontmatter.get("resource", "")),
                    " ".join(str(tag) for tag in tags if isinstance(tag, str)),
                ]
            )
            field_tokens = set(self._tokenize(fields))
            if not field_tokens:
                continue

            overlap = len(query_tokens.intersection(field_tokens))
            if overlap:
                seed_scores[doc.concept_id] += min(0.8, overlap / max(1, len(query_tokens)))

        ranked = sorted(seed_scores.items(), key=lambda pair: pair[1], reverse=True)
        return [concept_id for concept_id, _ in ranked[:limit] if concept_id in self._lookup]

    def _structured_scores(self, query: str) -> dict[str, float]:
        query_tokens = set(self._tokenize(query))
        if not query_tokens:
            return {}

        hinted_types = {
            concept_type
            for concept_type, hints in TYPE_HINTS.items()
            if query_tokens.intersection(hints)
        }

        scores: dict[str, float] = {}
        for doc in self._documents:
            score = 0.0
            frontmatter = doc.frontmatter
            doc_type = str(frontmatter.get("type", "concept")).lower()
            tags = frontmatter.get("tags", [])
            if not isinstance(tags, list):
                tags = []

            if hinted_types and doc_type in hinted_types:
                score += 0.65

            title_tokens = set(self._tokenize(str(frontmatter.get("title", ""))))
            resource_tokens = set(self._tokenize(str(frontmatter.get("resource", ""))))
            tag_tokens = set(
                token
                for tag in tags
                for token in self._tokenize(str(tag))
            )

            overlap = len(query_tokens.intersection(title_tokens.union(resource_tokens).union(tag_tokens)))
            if overlap:
                score += min(0.35, overlap / max(1, len(query_tokens)))

            if score > 0.0:
                scores[doc.concept_id] = min(1.0, score)

        return self._normalize(scores)

    def _effective_weights(
        self,
        route: str,
        has_semantic: bool,
        has_keyword: bool,
        has_graph: bool,
        has_structured: bool,
    ) -> dict[str, float]:
        base = BASE_ROUTE_WEIGHTS.get(route, BASE_ROUTE_WEIGHTS["hybrid"]).copy()

        if not has_semantic:
            base["semantic"] = 0.0
        if not has_keyword:
            base["keyword"] = 0.0
        if not has_graph:
            base["graph"] = 0.0
        if not has_structured:
            base["structured"] = 0.0

        total = sum(base.values())
        if total <= 0:
            return {"semantic": 0.0, "keyword": 1.0, "graph": 0.0, "structured": 0.0}

        return {key: value / total for key, value in base.items()}

    def _is_relationship_query(self, query: str) -> bool:
        lower = query.lower()
        return any(term in lower for term in GRAPH_INTENT_TERMS)

    def _normalize(self, scores: dict[str, float]) -> dict[str, float]:
        if not scores:
            return {}

        values = list(scores.values())
        minimum = min(values)
        maximum = max(values)

        if maximum <= minimum:
            return {
                key: (1.0 if maximum > 0 else 0.0)
                for key in scores
            }

        return {
            key: (value - minimum) / (maximum - minimum)
            for key, value in scores.items()
        }

    def _to_result(
        self,
        concept_id: str,
        score: float,
        source: str,
        score_breakdown: dict[str, float] | None = None,
        explanation_trace: list[str] | None = None,
    ) -> RetrievalResult:
        doc = self._lookup[concept_id]
        frontmatter = doc.frontmatter

        return RetrievalResult(
            concept_id=concept_id,
            path=doc.path.as_posix(),
            title=str(frontmatter.get("title", concept_id)),
            concept_type=str(frontmatter.get("type", "concept")),
            score=float(score),
            source=source,
            snippet=doc.body[:320],
            metadata={
                "type": str(frontmatter.get("type", "concept")),
                "title": str(frontmatter.get("title", concept_id)),
                "resource": str(frontmatter.get("resource", "")),
                "tags": ",".join(str(tag) for tag in frontmatter.get("tags", [])),
            },
            score_breakdown=score_breakdown or {},
            explanation_trace=explanation_trace or [],
        )

    def _load_documents(self, okf_dir: Path) -> list[DocumentRecord]:
        if not okf_dir.exists() or not okf_dir.is_dir():
            raise FileNotFoundError(f"OKF directory not found: {okf_dir}")

        documents: list[DocumentRecord] = []

        for path in sorted(okf_dir.rglob("*.md")):
            if not path.is_file() or path.name.lower() in RESERVED_FILES:
                continue

            frontmatter, body = self._parse_frontmatter(path)
            rel_path = path.resolve().relative_to(okf_dir.resolve()).as_posix()
            concept_id = rel_path[:-3] if rel_path.endswith(".md") else rel_path

            raw_text = "\n".join(
                [
                    str(frontmatter.get("title", "")),
                    str(frontmatter.get("description", "")),
                    body,
                ]
            ).strip()

            documents.append(
                DocumentRecord(
                    concept_id=concept_id,
                    path=path,
                    frontmatter=frontmatter,
                    body=body,
                    raw_text=raw_text,
                )
            )

        return documents

    def _parse_frontmatter(self, path: Path) -> tuple[dict[str, Any], str]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()

        if not lines or lines[0].strip() != "---":
            return {}, text

        end_idx = None
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                end_idx = idx
                break

        if end_idx is None:
            return {}, text

        frontmatter_text = "\n".join(lines[1:end_idx])
        body = "\n".join(lines[end_idx + 1 :]).strip()

        try:
            frontmatter = yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError as exc:
            logger.debug("invalid frontmatter while loading retrieval document %s: %s", path, exc)
            frontmatter = {}

        if not isinstance(frontmatter, dict):
            frontmatter = {}

        return frontmatter, body

    def _tokenize(self, text: str) -> list[str]:
        return [token.lower() for token in TOKEN_PATTERN.findall(text)]

    def _concept_id_from_vector_hit(self, raw_id: str, metadata: dict[str, Any] | None) -> str:
        if metadata and isinstance(metadata, dict):
            source_path = metadata.get("source_path")
            if isinstance(source_path, str) and source_path.strip():
                normalized = source_path.strip()
                return normalized[:-3] if normalized.endswith(".md") else normalized
        return str(raw_id)

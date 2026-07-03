"""Agentic assistant for grounded Q&A over OKF knowledge bundles."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import networkx as nx
import yaml

from rag.retriever import HybridSearchRouter, RetrievalResult, SearchRoute

logger = logging.getLogger(__name__)

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")
STRUCTURED_TERMS = {
    "owner",
    "owns",
    "owned",
    "depends",
    "depend",
    "dependency",
    "dependencies",
    "linked",
    "lineage",
    "upstream",
    "downstream",
    "schema",
    "table",
    "column",
    "formula",
    "runbook",
    "playbook",
}
SEMANTIC_TERMS = {"explain", "overview", "describe", "summary", "purpose", "why", "how"}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "what",
    "which",
    "who",
    "with",
}
RESERVED_FILES = {"index.md", "log.md", "readme.md"}


@dataclass(slots=True)
class AgentToolCall:
    """Tool invocation record for observability."""

    tool_name: str
    arguments: dict[str, Any]
    output_summary: str
    citations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AgentResponse:
    """Final assistant response payload."""

    answer: str
    citations: list[str]
    used_concepts: list[str]
    tool_trace: list[str]
    tool_calls: list[AgentToolCall] = field(default_factory=list)
    evidence_summary: str = ""
    confidence: float = 0.0
    supported: bool = True
    unsupported_reason: str | None = None
    strategy: str = "retrieval_first"

    def to_dict(self) -> dict[str, Any]:
        """Serialize response into JSON-ready dictionary."""

        payload = asdict(self)
        payload["tool_calls"] = [asdict(call) for call in self.tool_calls]
        return payload


@dataclass(slots=True)
class _LexicalDocument:
    """Indexed OKF document for lexical search tool."""

    concept_id: str
    path: Path
    title: str
    concept_type: str
    tags: list[str]
    body: str
    token_set: set[str]


class EnterpriseAssistant:
    """Enterprise agent with explicit tool calling and grounding safeguards.

    Tools:
    1. search_okf_documents
    2. search_vector_db
    3. traverse_knowledge_graph
    4. read_okf_file
    5. summarize_evidence

    The orchestration strategy is:
    - structured queries -> graph-first,
    - broad semantic queries -> retrieval-first.
    """

    def __init__(
        self,
        retriever: HybridSearchRouter,
        graph: nx.DiGraph,
        okf_dir: str | Path,
        llm: Any | None = None,
        max_context_files: int = 6,
        min_top_score: float = 0.2,
        min_evidence_hits: int = 1,
    ):
        self.retriever = retriever
        self.graph = graph
        self.okf_dir = Path(okf_dir)
        self.llm = llm
        self.max_context_files = max_context_files
        self.min_top_score = min_top_score
        self.min_evidence_hits = min_evidence_hits

        self._lexical_docs = self._load_lexical_docs()
        self._lexical_lookup = {doc.concept_id: doc for doc in self._lexical_docs}

    def search_okf_documents(self, query: str, top_k: int = 8) -> list[RetrievalResult]:
        """Tool: local lexical search over OKF pages."""

        query_tokens = set(self._tokenize(query)) - STOPWORDS
        if not query_tokens:
            return []

        hits: list[RetrievalResult] = []
        for doc in self._lexical_docs:
            overlap = len(query_tokens.intersection(doc.token_set))
            if overlap <= 0:
                continue

            title_tokens = set(self._tokenize(doc.title))
            title_boost = 0.25 if query_tokens.intersection(title_tokens) else 0.0
            score = min(1.0, (overlap / max(1, len(query_tokens))) + title_boost)

            hits.append(
                RetrievalResult(
                    concept_id=doc.concept_id,
                    path=doc.path.as_posix(),
                    title=doc.title,
                    concept_type=doc.concept_type,
                    score=float(score),
                    source="okf_keyword_tool",
                    snippet=doc.body[:320],
                    metadata={
                        "type": doc.concept_type,
                        "title": doc.title,
                        "resource": doc.path.as_posix(),
                        "tags": ",".join(doc.tags),
                    },
                    score_breakdown={
                        "semantic": 0.0,
                        "keyword": float(score),
                        "graph": 0.0,
                        "structured": 0.0,
                        "final": float(score),
                    },
                    explanation_trace=[
                        "tool=search_okf_documents",
                        f"token_overlap={overlap}",
                    ],
                )
            )

        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:top_k]

    def search_vector_db(
        self,
        query: str,
        top_k: int = 8,
        route: SearchRoute = "auto",
    ) -> list[RetrievalResult]:
        """Tool: hybrid/vector retrieval over persisted index."""

        return self.retriever.search(
            query=query,
            top_k=top_k,
            use_graph_expansion=True,
            route=route,
        )

    def query_knowledge_graph(
        self,
        concept_id: str,
        depth: int = 2,
        direction: Literal["out", "in", "both"] = "both",
    ) -> list[dict[str, str]]:
        """Tool: traverse graph neighbors for relation-based context."""

        if concept_id not in self.graph:
            return []

        discovered: list[dict[str, str]] = []
        frontier = {concept_id}
        visited = {concept_id}

        for hop in range(1, max(1, depth) + 1):
            next_frontier: set[str] = set()
            for node in frontier:
                neighbors: set[str] = set()
                if direction in {"out", "both"}:
                    neighbors.update(self.graph.successors(node))
                if direction in {"in", "both"}:
                    neighbors.update(self.graph.predecessors(node))

                for neighbor in neighbors:
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)
                    next_frontier.add(neighbor)

                    attrs = self.graph.nodes[neighbor]
                    discovered.append(
                        {
                            "concept_id": str(neighbor),
                            "title": str(attrs.get("title", neighbor)),
                            "type": str(attrs.get("type", "concept")),
                            "path": str(attrs.get("path", "")),
                            "hop": str(hop),
                        }
                    )

            frontier = next_frontier
            if not frontier:
                break

        return discovered

    def read_okf_file(self, concept_id: str) -> str:
        """Tool: read full markdown for one concept."""

        path = self.okf_dir / f"{concept_id}.md"
        if not path.exists() or not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def summarize_evidence(self, question: str, evidence_chunks: list[str]) -> str:
        """Tool: summarize evidence snippets into grounded context."""

        if not evidence_chunks:
            return "No supporting evidence snippets were collected."

        if self.llm is None:
            lines = ["Grounded evidence summary:"]
            for chunk in evidence_chunks[:4]:
                excerpt = chunk.strip().replace("\n", " ")
                lines.append(f"- {excerpt[:240]}")
            return "\n".join(lines)

        prompt = (
            "You are an enterprise knowledge summarizer.\n"
            "Summarize ONLY from the evidence snippets.\n"
            "If evidence is weak, explicitly say evidence is insufficient.\n\n"
            f"Question: {question}\n\n"
            "Evidence:\n"
            + "\n".join(f"- {item}" for item in evidence_chunks[:8])
            + "\n\nReturn concise markdown bullets."
        )

        try:
            response = self.llm.invoke(prompt)
            content = getattr(response, "content", response)
            if isinstance(content, list):
                return "\n".join(str(item) for item in content)
            return str(content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM evidence summarization failed: %s", exc)
            return "Evidence summarization degraded to heuristic mode due to LLM failure."

    def answer(self, question: str, top_k: int = 8) -> AgentResponse:
        """Answer a question with tool-calling orchestration and safeguards."""

        normalized_question = question.strip()
        if not normalized_question:
            return AgentResponse(
                answer="Question is empty. Please provide a specific enterprise knowledge question.",
                citations=[],
                used_concepts=[],
                tool_trace=["Validation: empty question rejected"],
                tool_calls=[],
                evidence_summary="No evidence",
                confidence=0.0,
                supported=False,
                unsupported_reason="empty_question",
                strategy="retrieval_first",
            )

        strategy, preferred_route = self._decide_strategy(normalized_question)
        tool_trace: list[str] = [f"Thought: strategy={strategy}, preferred_route={preferred_route}"]
        tool_calls: list[AgentToolCall] = []

        lexical_hits = self.search_okf_documents(normalized_question, top_k=max(top_k, 6))
        tool_trace.append(f"Action: search_okf_documents(query={normalized_question!r}) -> {len(lexical_hits)} hits")
        tool_calls.append(
            AgentToolCall(
                tool_name="search_okf_documents",
                arguments={"query": normalized_question, "top_k": max(top_k, 6)},
                output_summary=f"returned {len(lexical_hits)} lexical hits",
                citations=[hit.path for hit in lexical_hits[:3]],
            )
        )

        vector_hits = self.search_vector_db(
            normalized_question,
            top_k=max(top_k, 8),
            route=preferred_route,
        )
        tool_trace.append(
            f"Action: search_vector_db(query={normalized_question!r}, route={preferred_route!r}) -> {len(vector_hits)} hits"
        )
        tool_calls.append(
            AgentToolCall(
                tool_name="search_vector_db",
                arguments={"query": normalized_question, "top_k": max(top_k, 8), "route": preferred_route},
                output_summary=f"returned {len(vector_hits)} retrieval hits",
                citations=[hit.path for hit in vector_hits[:3]],
            )
        )

        combined_scores, best_hits = self._merge_hits(
            lexical_hits=lexical_hits,
            vector_hits=vector_hits,
            strategy=strategy,
        )

        graph_neighbors: list[dict[str, str]] = []
        if strategy == "graph_first":
            seed_ids = self._top_concepts(combined_scores, limit=3)
            for seed in seed_ids:
                neighbors = self.query_knowledge_graph(seed, depth=2, direction="both")
                if neighbors:
                    graph_neighbors.extend(neighbors)
                    tool_trace.append(f"Action: query_knowledge_graph(concept_id={seed!r}, depth=2) -> {len(neighbors)}")
                    tool_calls.append(
                        AgentToolCall(
                            tool_name="query_knowledge_graph",
                            arguments={"concept_id": seed, "depth": 2, "direction": "both"},
                            output_summary=f"returned {len(neighbors)} neighbors",
                            citations=[item["path"] for item in neighbors if item.get("path")][:4],
                        )
                    )

            for item in graph_neighbors:
                concept_id = item.get("concept_id", "").strip()
                if not concept_id:
                    continue
                combined_scores[concept_id] += 0.12
                if concept_id not in best_hits and concept_id in self._lexical_lookup:
                    doc = self._lexical_lookup[concept_id]
                    best_hits[concept_id] = RetrievalResult(
                        concept_id=concept_id,
                        path=doc.path.as_posix(),
                        title=doc.title,
                        concept_type=doc.concept_type,
                        score=combined_scores[concept_id],
                        source="graph_tool",
                        snippet=doc.body[:320],
                        metadata={
                            "type": doc.concept_type,
                            "title": doc.title,
                            "resource": doc.path.as_posix(),
                            "tags": ",".join(doc.tags),
                        },
                        score_breakdown={"graph": 1.0, "final": combined_scores[concept_id]},
                        explanation_trace=["tool=query_knowledge_graph", "neighbor_boost=0.12"],
                    )

        selected_concepts = self._top_concepts(combined_scores, limit=self.max_context_files)
        evidence_chunks: list[str] = []
        citations: list[str] = []
        used_concepts: list[str] = []
        ranked_hits: list[RetrievalResult] = []

        for concept_id in selected_concepts:
            hit = best_hits.get(concept_id)
            if hit is None:
                continue
            ranked_hits.append(hit)
            used_concepts.append(concept_id)
            citations.append(hit.path)

            file_text = self.read_okf_file(concept_id)
            if file_text:
                tool_trace.append(f"Action: read_okf_file(concept_id={concept_id!r})")
                tool_calls.append(
                    AgentToolCall(
                        tool_name="read_okf_file",
                        arguments={"concept_id": concept_id},
                        output_summary=f"loaded {len(file_text)} characters",
                        citations=[hit.path],
                    )
                )
            excerpt = self._extract_relevant_excerpt(file_text or hit.snippet, normalized_question)
            evidence_chunks.append(f"[{concept_id}] {excerpt} (source: {hit.path})")

        evidence_summary = self.summarize_evidence(normalized_question, evidence_chunks)
        tool_trace.append(f"Action: summarize_evidence(chunks={len(evidence_chunks)})")
        tool_calls.append(
            AgentToolCall(
                tool_name="summarize_evidence",
                arguments={"question": normalized_question, "chunks": len(evidence_chunks)},
                output_summary="generated grounded evidence summary",
                citations=sorted(set(citations)),
            )
        )

        supported, unsupported_reason = self._assess_support(
            question=normalized_question,
            hits=ranked_hits,
            evidence_chunks=evidence_chunks,
        )

        if supported:
            answer = self._compose_grounded_answer(normalized_question, evidence_summary, citations)
        else:
            answer = (
                "I do not have enough grounded evidence in the current OKF bundle to answer this reliably. "
                "Please refine the question or add the missing knowledge page."
            )

        confidence = self._confidence_score(ranked_hits, supported)

        return AgentResponse(
            answer=answer,
            citations=sorted(set(citations)),
            used_concepts=sorted(set(used_concepts)),
            tool_trace=tool_trace,
            tool_calls=tool_calls,
            evidence_summary=evidence_summary,
            confidence=confidence,
            supported=supported,
            unsupported_reason=unsupported_reason,
            strategy=strategy,
        )

    def _decide_strategy(self, question: str) -> tuple[str, SearchRoute]:
        tokens = set(self._tokenize(question))
        structured_signal = bool(tokens.intersection(STRUCTURED_TERMS))
        semantic_signal = bool(tokens.intersection(SEMANTIC_TERMS))

        if structured_signal:
            return "graph_first", "graph"
        if semantic_signal:
            return "retrieval_first", "vector"
        return "retrieval_first", "hybrid"

    def _merge_hits(
        self,
        lexical_hits: list[RetrievalResult],
        vector_hits: list[RetrievalResult],
        strategy: str,
    ) -> tuple[dict[str, float], dict[str, RetrievalResult]]:
        combined_scores: dict[str, float] = defaultdict(float)
        best_hits: dict[str, RetrievalResult] = {}

        lexical_weight = 0.45 if strategy == "graph_first" else 0.30
        vector_weight = 0.55 if strategy == "graph_first" else 0.70

        for hit in lexical_hits:
            combined_scores[hit.concept_id] += lexical_weight * hit.score
            previous = best_hits.get(hit.concept_id)
            if previous is None or hit.score > previous.score:
                best_hits[hit.concept_id] = hit

        for hit in vector_hits:
            combined_scores[hit.concept_id] += vector_weight * hit.score
            previous = best_hits.get(hit.concept_id)
            if previous is None or hit.score > previous.score:
                best_hits[hit.concept_id] = hit

        return combined_scores, best_hits

    def _top_concepts(self, scores: dict[str, float], limit: int) -> list[str]:
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return [concept_id for concept_id, _ in ranked[:limit]]

    def _assess_support(
        self,
        question: str,
        hits: list[RetrievalResult],
        evidence_chunks: list[str],
    ) -> tuple[bool, str | None]:
        if len(hits) < self.min_evidence_hits:
            return False, "no_retrieval_hits"

        top_score = max((hit.score for hit in hits), default=0.0)
        if top_score < self.min_top_score:
            return False, "low_retrieval_confidence"

        question_tokens = set(self._tokenize(question)) - STOPWORDS
        evidence_tokens = set(self._tokenize(" ".join(evidence_chunks))) - STOPWORDS
        overlap = question_tokens.intersection(evidence_tokens)

        required_overlap = 1 if len(question_tokens) <= 4 else 2
        if len(overlap) < required_overlap:
            return False, "no_lexical_evidence_overlap"

        return True, None

    def _confidence_score(self, hits: list[RetrievalResult], supported: bool) -> float:
        if not hits:
            return 0.0

        avg_top = sum(hit.score for hit in hits[:3]) / max(1, min(3, len(hits)))
        if not supported:
            return max(0.05, avg_top * 0.4)
        return min(1.0, 0.25 + (avg_top * 0.75))

    def _compose_grounded_answer(self, question: str, evidence_summary: str, citations: list[str]) -> str:
        if self.llm is None:
            return (
                f"Question: {question}\n\n"
                f"{evidence_summary}\n\n"
                "Grounding: The answer is based only on retrieved OKF evidence."
            )

        prompt = (
            "You are a grounded enterprise OKF assistant.\n"
            "Rules:\n"
            "1) Answer ONLY from supplied evidence summary.\n"
            "2) If evidence is incomplete, explicitly mention the missing fact.\n"
            "3) Do not invent owners, formulas, or dependencies.\n\n"
            f"Question: {question}\n\n"
            f"Evidence summary:\n{evidence_summary}\n\n"
            "Return concise markdown answer."
        )

        try:
            response = self.llm.invoke(prompt)
            content = getattr(response, "content", response)
            answer = "\n".join(str(item) for item in content) if isinstance(content, list) else str(content)
            if citations:
                answer = f"{answer}\n\nSources: {', '.join(sorted(set(citations)))}"
            return answer
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM answer generation failed: %s", exc)
            return (
                f"Question: {question}\n\n"
                f"{evidence_summary}\n\n"
                "Grounding: Degraded to heuristic response due to LLM failure."
            )

    def _extract_relevant_excerpt(self, text: str, question: str, max_chars: int = 360) -> str:
        if not text.strip():
            return "No text available."

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return text[:max_chars]

        question_tokens = set(self._tokenize(question)) - STOPWORDS
        if not question_tokens:
            return lines[0][:max_chars]

        best_line = lines[0]
        best_score = 0
        for line in lines:
            line_tokens = set(self._tokenize(line))
            score = len(question_tokens.intersection(line_tokens))
            if score > best_score:
                best_score = score
                best_line = line

        return best_line[:max_chars]

    def _load_lexical_docs(self) -> list[_LexicalDocument]:
        documents: list[_LexicalDocument] = []
        if not self.okf_dir.exists() or not self.okf_dir.is_dir():
            return documents

        for path in sorted(self.okf_dir.rglob("*.md")):
            if not path.is_file() or path.name.lower() in RESERVED_FILES:
                continue
            frontmatter, body = self._parse_frontmatter(path)
            rel_path = path.resolve().relative_to(self.okf_dir.resolve()).as_posix()
            concept_id = rel_path[:-3] if rel_path.endswith(".md") else rel_path
            title = str(frontmatter.get("title", concept_id))
            concept_type = str(frontmatter.get("type", "concept"))

            tags = frontmatter.get("tags", [])
            if not isinstance(tags, list):
                tags = []
            normalized_tags = [str(tag) for tag in tags]

            raw = " ".join([title, str(frontmatter.get("description", "")), body, " ".join(normalized_tags)])
            token_set = set(self._tokenize(raw))

            documents.append(
                _LexicalDocument(
                    concept_id=concept_id,
                    path=path,
                    title=title,
                    concept_type=concept_type,
                    tags=normalized_tags,
                    body=body,
                    token_set=token_set,
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
        except yaml.YAMLError:
            frontmatter = {}

        if not isinstance(frontmatter, dict):
            frontmatter = {}
        return frontmatter, body

    def _tokenize(self, text: str) -> list[str]:
        return [token.lower() for token in TOKEN_PATTERN.findall(text or "")]

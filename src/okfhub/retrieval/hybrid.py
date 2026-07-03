"""Hybrid retrieval combining lexical, vector, and graph expansion."""

import re
from collections import defaultdict

import numpy as np
from rank_bm25 import BM25Okapi

from okfhub.embeddings import ChromaConceptStore
from okfhub.graph import Neo4jGraphStore
from okfhub.llm import OllamaClient
from okfhub.models import ConceptDocument, RetrievalHit

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")


class HybridRetriever:
    """Hybrid retrieval over OKF concept documents.

    Combines lexical BM25 hits with vector similarity and optional graph expansion.
    """

    def __init__(
        self,
        docs: list[ConceptDocument],
        vector_store: ChromaConceptStore,
        ollama: OllamaClient,
        graph_store: Neo4jGraphStore | None = None,
    ):
        self._docs = docs
        self._by_id = {doc.concept_id: doc for doc in docs}
        self._vector_store = vector_store
        self._ollama = ollama
        self._graph_store = graph_store

        self._tokens = [self._tokenize(self._doc_text(doc)) for doc in docs]
        self._bm25 = BM25Okapi(self._tokens) if self._tokens else None

    async def search(self, query: str, top_k: int = 8) -> list[RetrievalHit]:
        """Search with hybrid ranking and graph-aware boosts."""

        combined_scores: dict[str, float] = defaultdict(float)

        # Lexical
        if self._bm25 is not None and self._docs:
            query_tokens = self._tokenize(query)
            bm25_scores = self._bm25.get_scores(query_tokens)
            for idx, score in enumerate(bm25_scores):
                concept_id = self._docs[idx].concept_id
                combined_scores[concept_id] += self._normalize(float(score), bm25_scores) * 0.45

        # Vector
        query_vector = (await self._ollama.embed([query]))[0]
        vector_hits = self._vector_store.query(query_vector, top_k=max(top_k, 12))
        for hit in vector_hits:
            combined_scores[hit.concept_id] += hit.score * 0.45

        # Graph expansion around strong seeds
        if self._graph_store is not None:
            seed_ids = sorted(combined_scores, key=combined_scores.get, reverse=True)[: min(4, len(combined_scores))]
            for seed in seed_ids:
                for neighbor in self._graph_store.neighbors(seed, depth=1, limit=10):
                    combined_scores[neighbor.concept_id] += 0.10

        ranked = sorted(combined_scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
        hits: list[RetrievalHit] = []
        for concept_id, score in ranked:
            doc = self._by_id.get(concept_id)
            if not doc:
                continue
            hits.append(
                RetrievalHit(
                    concept_id=concept_id,
                    score=float(score),
                    content=self._doc_text(doc),
                    source_path=doc.relative_path,
                    metadata={
                        "title": doc.frontmatter.title,
                        "type": doc.frontmatter.type,
                    },
                )
            )

        return hits

    def _doc_text(self, doc: ConceptDocument) -> str:
        return f"{doc.frontmatter.title}\n{doc.frontmatter.description}\n{doc.body}"

    def _tokenize(self, text: str) -> list[str]:
        return [token.lower() for token in TOKEN_PATTERN.findall(text)]

    def _normalize(self, score: float, all_scores: np.ndarray) -> float:
        min_score = float(np.min(all_scores))
        max_score = float(np.max(all_scores))
        if max_score <= min_score:
            return 0.0
        return (score - min_score) / (max_score - min_score)

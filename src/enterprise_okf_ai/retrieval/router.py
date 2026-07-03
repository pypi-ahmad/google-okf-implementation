"""Hybrid retrieval service wrappers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from enterprise_okf_ai.graph.builder import GraphService
from rag.retriever import HybridSearchRouter, RetrievalResult, SearchResponse, SearchRoute
from vector_db.indexer import ChromaVectorStore


class RetrievalService:
    """Semantic + lexical + graph-aware retrieval over OKF content."""

    def __init__(self, router: HybridSearchRouter):
        self._router = router

    @property
    def router(self) -> HybridSearchRouter:
        """Expose underlying router for advanced retrieval and evaluation surfaces."""

        return self._router

    @classmethod
    def from_okf(
        cls,
        okf_dir: str | Path,
        vector_dir: str | Path,
        embedding_fn: Callable[[list[str]], list[list[float]]],
        include_graph: bool = True,
    ) -> RetrievalService:
        """Construct retrieval service from persisted OKF and vector assets."""

        graph = GraphService(okf_dir).build() if include_graph else None
        router = HybridSearchRouter(
            okf_dir=okf_dir,
            vector_store=ChromaVectorStore(vector_dir),
            embedding_fn=embedding_fn,
            graph=graph,
        )
        return cls(router)

    def search(
        self,
        query: str,
        top_k: int = 8,
        route: SearchRoute = "auto",
    ) -> list[RetrievalResult]:
        """Run retrieval query using auto or explicit routing strategy."""

        return self._router.search(
            query=query,
            top_k=top_k,
            use_graph_expansion=True,
            route=route,
        )

    def search_with_trace(
        self,
        query: str,
        top_k: int = 8,
        route: SearchRoute = "auto",
    ) -> SearchResponse:
        """Run retrieval query and return routing explanation traces."""

        return self._router.search_with_trace(
            query=query,
            top_k=top_k,
            use_graph_expansion=True,
            route=route,
        )

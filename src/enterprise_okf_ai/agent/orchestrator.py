"""Agent orchestration wrappers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from agent.assistant import AgentResponse, EnterpriseAssistant
from enterprise_okf_ai.graph.builder import GraphService
from enterprise_okf_ai.retrieval.router import RetrievalService


class AgentOrchestrator:
    """Create and run enterprise Q&A agent workflows."""

    def __init__(self, assistant: EnterpriseAssistant):
        self._assistant = assistant

    @classmethod
    def from_okf(
        cls,
        okf_dir: str | Path,
        vector_dir: str | Path,
        embedding_fn: Callable[[list[str]], list[list[float]]],
        llm: Any | None = None,
    ) -> AgentOrchestrator:
        """Construct agent from persisted retrieval and graph resources."""

        retrieval = RetrievalService.from_okf(
            okf_dir=okf_dir,
            vector_dir=vector_dir,
            embedding_fn=embedding_fn,
            include_graph=True,
        )
        graph = GraphService(okf_dir).build()

        assistant = EnterpriseAssistant(
            retriever=retrieval.router,
            graph=graph,
            okf_dir=okf_dir,
            llm=llm,
        )
        return cls(assistant)

    def ask(self, question: str, top_k: int = 8) -> AgentResponse:
        """Execute agentic question-answering over enterprise OKF knowledge."""

        return self._assistant.answer(question=question, top_k=top_k)

"""LangGraph-based enterprise knowledge agent."""

from __future__ import annotations

from typing import TypedDict

from loguru import logger

from okfhub.graph import Neo4jGraphStore
from okfhub.llm import OllamaClient
from okfhub.models import AgentAnswer, ConceptDocument, RetrievalHit
from okfhub.retrieval import HybridRetriever


class AgentState(TypedDict, total=False):
    """State tracked through LangGraph workflow."""

    question: str
    hits: list[RetrievalHit]
    context: str
    citations: list[str]
    answer: str
    confidence: float
    abstained: bool


class EnterpriseKnowledgeAgent:
    """Enterprise QA agent exposing retrieval and graph-aware tools."""

    def __init__(
        self,
        retriever: HybridRetriever,
        ollama: OllamaClient,
        documents: list[ConceptDocument],
        graph_store: Neo4jGraphStore | None = None,
    ):
        self._retriever = retriever
        self._ollama = ollama
        self._graph_store = graph_store
        self._documents = {doc.concept_id: doc for doc in documents}
        self._workflow = self._build_workflow()

    async def ask(self, question: str) -> AgentAnswer:
        """Answer a knowledge question with citations and abstention logic.

        Example:
            >>> # await agent.ask("How is MAU computed?")
        """

        if self._workflow is None:
            return await self._ask_fallback(question)

        state = await self._workflow.ainvoke({"question": question})
        return AgentAnswer(
            answer=str(state.get("answer", "")),
            citations=[str(c) for c in state.get("citations", [])],
            used_concepts=[hit.concept_id for hit in state.get("hits", [])],
            confidence=float(state.get("confidence", 0.0)),
            abstained=bool(state.get("abstained", False)),
        )

    async def search_okf(self, query: str, top_k: int = 8) -> list[RetrievalHit]:
        """Tool: hybrid retrieval over OKF concepts."""

        return await self._retriever.search(query=query, top_k=top_k)

    def read_markdown(self, concept_id: str) -> str:
        """Tool: read concept markdown content."""

        doc = self._documents.get(concept_id)
        if doc is None:
            return ""
        return f"# {doc.frontmatter.title}\n\n{doc.body}"

    def traverse_graph(self, concept_id: str, depth: int = 1) -> list[str]:
        """Tool: traverse graph neighbors for context expansion."""

        if self._graph_store is None:
            return []
        return [n.concept_id for n in self._graph_store.neighbors(concept_id=concept_id, depth=depth)]

    async def summarize(self, text: str) -> str:
        """Tool: summarize context before final response."""

        prompt = (
            "Summarize the following enterprise documentation context into concise bullet points "
            "without adding facts.\n\n"
            f"{text}"
        )
        return await self._ollama.chat_text(prompt)

    def _build_workflow(self):
        try:
            from langgraph.graph import END, StateGraph
        except Exception as exc:  # noqa: BLE001
            logger.warning("LangGraph unavailable, using fallback flow: {}", exc)
            return None

        graph = StateGraph(AgentState)

        async def retrieve(state: AgentState) -> AgentState:
            hits = await self.search_okf(state["question"], top_k=8)
            return {"hits": hits}

        async def build_context(state: AgentState) -> AgentState:
            hits = state.get("hits", [])
            if not hits:
                return {
                    "context": "",
                    "citations": [],
                    "abstained": True,
                    "confidence": 0.0,
                    "answer": "I could not find grounded evidence in the knowledge base.",
                }

            snippets: list[str] = []
            citations: list[str] = []
            for hit in hits[:6]:
                citations.append(hit.source_path)
                snippets.append(
                    f"[Concept: {hit.concept_id}]\nSource: {hit.source_path}\nScore: {hit.score:.3f}\n{hit.content[:1200]}"
                )

            return {
                "context": "\n\n".join(snippets),
                "citations": citations,
                "abstained": False,
                "confidence": min(1.0, sum(h.score for h in hits[:3]) / 3),
            }

        async def answer(state: AgentState) -> AgentState:
            if state.get("abstained", False):
                return state

            prompt = (
                "You are an enterprise knowledge assistant. Answer using only the supplied context. "
                "If unsure, say so. Include direct references to concept IDs when possible.\n\n"
                f"QUESTION:\n{state['question']}\n\n"
                f"CONTEXT:\n{state['context']}\n\n"
                "Return plain text answer, concise and factual."
            )
            output = await self._ollama.chat_text(prompt)
            return {"answer": output or "No grounded answer generated.", "abstained": False}

        graph.add_node("retrieve", retrieve)
        graph.add_node("build_context", build_context)
        graph.add_node("answer", answer)

        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "build_context")
        graph.add_edge("build_context", "answer")
        graph.add_edge("answer", END)

        return graph.compile()

    async def _ask_fallback(self, question: str) -> AgentAnswer:
        hits = await self.search_okf(question, top_k=8)
        if not hits:
            return AgentAnswer(
                answer="I could not find grounded evidence in the knowledge base.",
                citations=[],
                used_concepts=[],
                confidence=0.0,
                abstained=True,
            )

        context = "\n\n".join(
            f"[{hit.concept_id}] {hit.content[:1200]}" for hit in hits[:6]
        )
        prompt = (
            "Answer the question using only context below. Be concise and cite concept IDs.\n\n"
            f"Question: {question}\n\nContext:\n{context}"
        )
        answer = await self._ollama.chat_text(prompt)
        return AgentAnswer(
            answer=answer,
            citations=[hit.source_path for hit in hits[:6]],
            used_concepts=[hit.concept_id for hit in hits[:6]],
            confidence=min(1.0, sum(h.score for h in hits[:3]) / 3),
            abstained=False,
        )

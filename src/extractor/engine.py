"""LLM-powered enterprise concept extraction engine."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from extractor.schema import EnterpriseConcepts


class ConceptExtractionEngine:
    """Extract structured enterprise concepts from unstructured text.

    The engine expects a LangChain-compatible chat model instance.
    It uses structured output when available, and falls back to JSON parsing.

    Example:
        >>> # llm = YourLangChainChatModel(...)
        >>> # engine = ConceptExtractionEngine(llm)
        >>> # concepts = engine.extract("API docs text")
    """

    def __init__(self, llm: Any):
        self._llm = llm
        self._prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You extract enterprise knowledge concepts from documents. "
                    "Return precise, non-duplicated, high-confidence outputs only.",
                ),
                (
                    "user",
                    "Extract Entities, Datasets, APIs, Tables, Metrics, and Glossary Terms from the text below. "
                    "Use structured output and keep descriptions factual.\n\n"
                    "SOURCE: {source}\n"
                    "TEXT:\n{text}",
                ),
            ]
        )

    def extract(self, text: str, source: str = "unknown") -> EnterpriseConcepts:
        """Extract validated enterprise concepts from raw text."""

        if not text.strip():
            return EnterpriseConcepts()

        try:
            structured_llm = self._llm.with_structured_output(EnterpriseConcepts)
            chain = self._prompt | structured_llm
            result = chain.invoke({"source": source, "text": text})
            return self._normalize(result)
        except Exception:
            payload = self._fallback_extract(text=text, source=source)
            return EnterpriseConcepts.model_validate(payload)

    def _fallback_extract(self, text: str, source: str) -> dict[str, object]:
        prompt = (
            "Return JSON only with keys: entities, datasets, apis, tables, metrics, glossary_terms. "
            "Each key must contain a list of objects using consistent fields for each concept type.\n\n"
            f"SOURCE: {source}\n"
            f"TEXT:\n{text}"
        )

        response = self._llm.invoke(prompt)
        content = getattr(response, "content", response)

        if isinstance(content, list):
            joined = "\n".join(str(item) for item in content)
            return self._parse_json(joined)
        return self._parse_json(str(content))

    def _parse_json(self, value: str) -> dict[str, object]:
        cleaned = value.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("Extractor output must be a JSON object")
        return parsed

    def _normalize(self, result: Any) -> EnterpriseConcepts:
        if isinstance(result, EnterpriseConcepts):
            return result
        if isinstance(result, dict):
            return EnterpriseConcepts.model_validate(result)
        if hasattr(result, "model_dump"):
            return EnterpriseConcepts.model_validate(result.model_dump())
        raise ValueError("Unsupported structured output type from LLM extraction")

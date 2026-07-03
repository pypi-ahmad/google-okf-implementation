"""LLM-driven concept extraction from ingested chunks."""

from collections import defaultdict

from loguru import logger

from okfhub.llm import OllamaClient
from okfhub.models import DocumentChunk, ExtractedConcept
from okfhub.utils.filesystem import sha256_text


class KnowledgeExtractor:
    """Extract enterprise concepts from normalized chunks using local LLM."""

    def __init__(self, ollama: OllamaClient):
        self._ollama = ollama

    async def extract(self, chunks: list[DocumentChunk]) -> list[ExtractedConcept]:
        """Extract and merge concepts from chunk-level prompts.

        Args:
            chunks: Input chunks from ingestion.

        Returns:
            De-duplicated concept list.
        """

        extracted: list[ExtractedConcept] = []
        for chunk in chunks:
            response = await self._ollama.chat_json(self._prompt(chunk.text))
            concepts = response.get("concepts", []) if isinstance(response, dict) else []

            if not isinstance(concepts, list):
                logger.warning("Skipping malformed extraction payload")
                continue

            for concept in concepts:
                parsed = self._parse_concept(concept=concept, chunk=chunk)
                if parsed:
                    extracted.append(parsed)

        merged = self._merge_concepts(extracted)
        logger.info("Extracted {} concepts ({} raw)", len(merged), len(extracted))
        return merged

    def _parse_concept(self, concept: object, chunk: DocumentChunk) -> ExtractedConcept | None:
        if not isinstance(concept, dict):
            return None

        concept_type = str(concept.get("type", "")).strip().lower()
        title = str(concept.get("title", "")).strip()
        description = str(concept.get("description", "")).strip()
        if not concept_type or not title or not description:
            return None

        resource = concept.get("resource")
        cid_seed = f"{concept_type}:{title.lower()}"
        concept_id = sha256_text(cid_seed)[:16]

        def _str_list(value: object) -> list[str]:
            if not isinstance(value, list):
                return []
            return [str(v).strip() for v in value if str(v).strip()]

        return ExtractedConcept(
            concept_id=concept_id,
            concept_type=concept_type,
            title=title,
            description=description,
            tags=_str_list(concept.get("tags")),
            resource=str(resource) if isinstance(resource, str) else chunk.source_path.as_posix(),
            owners=_str_list(concept.get("owners")),
            dependencies=_str_list(concept.get("dependencies")),
            aliases=_str_list(concept.get("aliases")),
            evidence_chunk_ids=[chunk.chunk_id],
        )

    def _merge_concepts(self, concepts: list[ExtractedConcept]) -> list[ExtractedConcept]:
        grouped: dict[str, list[ExtractedConcept]] = defaultdict(list)
        for concept in concepts:
            key = f"{concept.concept_type}:{concept.title.lower().strip()}"
            grouped[key].append(concept)

        merged: list[ExtractedConcept] = []
        for group in grouped.values():
            base = group[0].model_copy(deep=True)
            base.tags = sorted({tag for item in group for tag in item.tags})
            base.owners = sorted({owner for item in group for owner in item.owners})
            base.dependencies = sorted({dep for item in group for dep in item.dependencies})
            base.aliases = sorted({alias for item in group for alias in item.aliases})
            base.evidence_chunk_ids = sorted({cid for item in group for cid in item.evidence_chunk_ids})
            merged.append(base)

        return sorted(merged, key=lambda item: (item.concept_type, item.title.lower()))

    def _prompt(self, text: str) -> str:
        return (
            "Extract enterprise knowledge concepts from the text below. Return JSON with key `concepts`. "
            "Each concept must include: type, title, description, tags[], owners[], dependencies[], aliases[], "
            "resource.\n"
            "Allowed `type`: entity, dataset, api, table, metric, owner, glossary, dependency, playbook, service.\n"
            "Return only high-confidence concepts present in the text.\n\n"
            f"TEXT:\n{text}"
        )

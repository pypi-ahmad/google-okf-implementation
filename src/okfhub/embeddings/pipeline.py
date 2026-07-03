"""Embedding generation pipeline over OKF concept documents."""

from okfhub.llm import OllamaClient
from okfhub.models import ConceptDocument

from .chroma_store import ChromaConceptStore


class EmbeddingPipeline:
    """Generate and persist embeddings for concept documents."""

    def __init__(self, ollama: OllamaClient, store: ChromaConceptStore):
        self._ollama = ollama
        self._store = store

    async def index_documents(self, docs: list[ConceptDocument]) -> None:
        """Embed docs and upsert to Chroma with metadata."""

        if not docs:
            return

        texts = [self._to_embedding_text(doc) for doc in docs]
        embeddings = await self._ollama.embed(texts)

        concept_ids = [doc.concept_id for doc in docs]
        metadatas = [
            {
                "type": doc.frontmatter.type,
                "title": doc.frontmatter.title,
                "source_path": doc.relative_path,
                "resource": doc.frontmatter.resource or "",
            }
            for doc in docs
        ]

        self._store.upsert(
            concept_ids=concept_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

    def _to_embedding_text(self, doc: ConceptDocument) -> str:
        return (
            f"Title: {doc.frontmatter.title}\n"
            f"Type: {doc.frontmatter.type}\n"
            f"Description: {doc.frontmatter.description}\n"
            f"Tags: {', '.join(doc.frontmatter.tags)}\n"
            f"Content:\n{doc.body}"
        )

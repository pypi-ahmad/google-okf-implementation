"""Chroma persistence for concept embeddings."""

from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection

from okfhub.models import RetrievalHit


class ChromaConceptStore:
    """Persistent Chroma wrapper for concept embeddings."""

    def __init__(self, persist_directory: Path, collection_name: str = "okf_concepts"):
        self._client = chromadb.PersistentClient(path=str(persist_directory))
        self._collection: Collection = self._client.get_or_create_collection(collection_name)

    def upsert(
        self,
        concept_ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, str]],
    ) -> None:
        """Upsert concept vectors and metadata."""

        if not concept_ids:
            return

        self._collection.upsert(
            ids=concept_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def query(self, query_embedding: list[float], top_k: int = 8) -> list[RetrievalHit]:
        """Run similarity query against stored concept vectors."""

        result = self._collection.query(query_embeddings=[query_embedding], n_results=top_k)

        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        hits: list[RetrievalHit] = []
        for concept_id, doc, meta, distance in zip(ids, docs, metas, distances, strict=False):
            score = 1.0 / (1.0 + float(distance))
            metadata = {k: str(v) for k, v in (meta or {}).items()}
            hits.append(
                RetrievalHit(
                    concept_id=str(concept_id),
                    score=score,
                    content=str(doc),
                    source_path=metadata.get("source_path", ""),
                    metadata=metadata,
                )
            )

        return hits

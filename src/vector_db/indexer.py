"""Idempotent OKF embedding indexer with local Chroma storage."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import chromadb
import yaml

RESERVED_FILES = {"index.md", "log.md", "readme.md"}


@dataclass(slots=True)
class ChunkedDocument:
    """Single chunk extracted from one OKF concept document."""

    chunk_id: str
    text: str
    metadata: dict[str, str]


class ChromaVectorStore:
    """Local Chroma wrapper for upsert/delete/query operations."""

    def __init__(self, persist_dir: str | Path, collection_name: str = "okf_documents"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        self._collection = self._client.get_or_create_collection(collection_name)

    def upsert(self, chunks: list[ChunkedDocument], embeddings: list[list[float]]) -> None:
        """Upsert chunks and vectors into Chroma collection."""

        if not chunks:
            return

        self._collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            embeddings=embeddings,
            documents=[chunk.text for chunk in chunks],
            metadatas=[chunk.metadata for chunk in chunks],
        )

    def delete(self, ids: list[str]) -> None:
        """Delete chunk IDs from collection."""

        if ids:
            self._collection.delete(ids=ids)

    def query(self, embedding: list[float], top_k: int = 8) -> dict[str, Any]:
        """Query vectors by a single embedding and return raw Chroma payload."""

        return self._collection.query(query_embeddings=[embedding], n_results=top_k)


class OKFVectorIndexer:
    """Chunk and embed OKF markdown documents into local vector storage.

    Design goals:
    - Idempotent indexing (only changed files are updated)
    - Metadata preservation from YAML frontmatter
    - Pluggable embeddings (SentenceTransformers or OpenAI)

    Example:
        >>> indexer = OKFVectorIndexer(okf_dir="okf_bundle", persist_dir="vector_db/chroma")
        >>> stats = indexer.index()
    """

    def __init__(
        self,
        okf_dir: str | Path,
        persist_dir: str | Path,
        collection_name: str = "okf_documents",
        embedding_provider: str = "sentence-transformers",
        embedding_model: str = "all-MiniLM-L6-v2",
        openai_model: str = "text-embedding-3-small",
        openai_api_key: str | None = None,
        chunk_size: int = 1200,
        chunk_overlap: int = 200,
        vector_store: ChromaVectorStore | None = None,
        embedding_fn: Callable[[list[str]], list[list[float]]] | None = None,
    ):
        self.okf_dir = Path(okf_dir)
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.openai_model = openai_model
        self.openai_api_key = openai_api_key
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self._vector_store = vector_store or ChromaVectorStore(self.persist_dir, collection_name=collection_name)
        self._embedding_fn = embedding_fn
        self._embedding_model_cache: Any = None

        self._manifest_path = self.persist_dir / ".okf_index_manifest.json"

    def index(self) -> dict[str, int]:
        """Run idempotent indexing and return update statistics."""

        if not self.okf_dir.exists() or not self.okf_dir.is_dir():
            raise FileNotFoundError(f"OKF directory not found: {self.okf_dir}")

        manifest = self._load_manifest()
        tracked_files = manifest.get("files", {})

        current_files = sorted(
            path
            for path in self.okf_dir.rglob("*.md")
            if path.is_file() and path.name.lower() not in RESERVED_FILES
        )
        current_rel_paths = {self._relative(path) for path in current_files}

        removed_paths = sorted(set(tracked_files.keys()) - current_rel_paths)
        removed_chunk_ids: list[str] = []
        for rel_path in removed_paths:
            entry = tracked_files.pop(rel_path, {})
            removed_chunk_ids.extend(entry.get("chunk_ids", []))

        self._vector_store.delete(removed_chunk_ids)

        changed_chunks: list[ChunkedDocument] = []
        changed_paths = 0
        deleted_chunk_ids: list[str] = []

        for file_path in current_files:
            rel_path = self._relative(file_path)
            checksum = self._file_checksum(file_path)
            previous = tracked_files.get(rel_path)

            if previous and previous.get("checksum") == checksum:
                continue

            changed_paths += 1
            if previous:
                deleted_chunk_ids.extend(previous.get("chunk_ids", []))

            frontmatter, body = self._parse_frontmatter(file_path)
            chunks = self._chunk_document(
                rel_path=rel_path,
                checksum=checksum,
                body=body,
                frontmatter=frontmatter,
            )
            changed_chunks.extend(chunks)
            tracked_files[rel_path] = {
                "checksum": checksum,
                "chunk_ids": [chunk.chunk_id for chunk in chunks],
                "updated_at": self._utc_now(),
            }

        self._vector_store.delete(deleted_chunk_ids)

        if changed_chunks:
            embeddings = self._embed_texts([chunk.text for chunk in changed_chunks])
            self._vector_store.upsert(changed_chunks, embeddings)

        manifest["files"] = tracked_files
        manifest["updated_at"] = self._utc_now()
        self._save_manifest(manifest)

        return {
            "files_scanned": len(current_files),
            "files_changed": changed_paths,
            "files_removed": len(removed_paths),
            "chunks_indexed": len(changed_chunks),
            "chunks_deleted": len(deleted_chunk_ids) + len(removed_chunk_ids),
        }

    def _chunk_document(
        self,
        rel_path: str,
        checksum: str,
        body: str,
        frontmatter: dict[str, Any],
    ) -> list[ChunkedDocument]:
        text = body.strip()
        if not text:
            return []

        title = str(frontmatter.get("title", Path(rel_path).stem))
        description = str(frontmatter.get("description", "")).strip()
        prefix = f"Title: {title}\nDescription: {description}\n\n" if description else f"Title: {title}\n\n"
        full_text = prefix + text

        chunks: list[ChunkedDocument] = []
        start = 0
        chunk_index = 0
        while start < len(full_text):
            end = min(start + self.chunk_size, len(full_text))
            chunk_text = full_text[start:end]

            chunk_hash = sha256(f"{rel_path}:{checksum}:{chunk_index}".encode()).hexdigest()[:20]
            chunk_id = f"{rel_path.replace('/', '_')}::{chunk_hash}"

            tags = frontmatter.get("tags", [])
            if not isinstance(tags, list):
                tags = []

            metadata = {
                "source_path": rel_path,
                "type": str(frontmatter.get("type", "concept")),
                "title": title,
                "resource": str(frontmatter.get("resource", "")),
                "tags": ",".join(str(tag) for tag in tags),
                "timestamp": str(frontmatter.get("timestamp", "")),
                "checksum": checksum,
                "chunk_index": str(chunk_index),
            }
            chunks.append(ChunkedDocument(chunk_id=chunk_id, text=chunk_text, metadata=metadata))

            if end >= len(full_text):
                break

            start = max(0, end - self.chunk_overlap)
            chunk_index += 1

        return chunks

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self._embedding_fn is not None:
            return self._embedding_fn(texts)

        if self.embedding_provider == "sentence-transformers":
            return self._embed_with_sentence_transformers(texts)
        if self.embedding_provider == "openai":
            return self._embed_with_openai(texts)

        raise ValueError(
            "Unsupported embedding provider. Use `sentence-transformers` or `openai`."
        )

    def _embed_with_sentence_transformers(self, texts: list[str]) -> list[list[float]]:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # noqa: BLE001
            raise ImportError(
                "sentence-transformers is required for embedding_provider='sentence-transformers'. "
                "Install it with: uv add sentence-transformers"
            ) from exc

        if self._embedding_model_cache is None:
            self._embedding_model_cache = SentenceTransformer(self.embedding_model)

        vectors = self._embedding_model_cache.encode(texts, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]

    def _embed_with_openai(self, texts: list[str]) -> list[list[float]]:
        try:
            from openai import OpenAI
        except ImportError as exc:  # noqa: BLE001
            raise ImportError(
                "openai package is required for embedding_provider='openai'. "
                "Install it with: uv add openai"
            ) from exc

        api_key = self.openai_api_key
        if not api_key:
            raise ValueError("OPENAI API key is required for embedding_provider='openai'.")

        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(model=self.openai_model, input=texts)
        return [item.embedding for item in response.data]

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

    def _load_manifest(self) -> dict[str, Any]:
        if not self._manifest_path.exists():
            return {"files": {}, "updated_at": None}

        try:
            payload = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {"files": {}, "updated_at": None}

        if not isinstance(payload, dict):
            return {"files": {}, "updated_at": None}

        payload.setdefault("files", {})
        return payload

    def _save_manifest(self, payload: dict[str, Any]) -> None:
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.okf_dir.resolve()).as_posix()

    def _file_checksum(self, path: Path) -> str:
        return sha256(path.read_bytes()).hexdigest()

    def _utc_now(self) -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()

"""Application settings and environment configuration."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the OKF platform.

    Attributes:
        ollama_base_url: Ollama server base URL.
        ollama_chat_model: Local chat model for extraction and QA.
        ollama_embed_model: Local embedding model.
        chroma_persist_directory: Chroma persistence directory.
        neo4j_uri: Neo4j connection URI.
        neo4j_user: Neo4j username.
        neo4j_password: Neo4j password.
        okf_root: Default output path for OKF bundle.
        synthetic_data_root: Default path for synthetic corpus outputs.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_chat_model: str = Field(default="qwen3:8b")
    ollama_embed_model: str = Field(default="nomic-embed-text")

    chroma_persist_directory: Path = Field(default=Path("vector_db/chroma"))

    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="neo4j")

    okf_root: Path = Field(default=Path("okf_bundle"))
    synthetic_data_root: Path = Field(default=Path("data/raw"))

    max_chunk_chars: int = Field(default=1800)
    chunk_overlap_chars: int = Field(default=200)
    retrieval_top_k: int = Field(default=8)

    validation_fail_on_warnings: bool = Field(default=False)


settings = Settings()

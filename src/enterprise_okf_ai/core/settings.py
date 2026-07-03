"""Application settings for enterprise OKF AI."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables.

    Example:
        >>> settings = Settings()
        >>> settings.okf_dir
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = Field(default="enterprise-okf-ai")
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3])

    data_dir: Path = Field(default=Path("data"))
    raw_data_dir: Path = Field(default=Path("data/raw"))
    okf_dir: Path = Field(default=Path("okf_bundle"))
    vector_dir: Path = Field(default=Path("vector_db/chroma"))
    graph_dir: Path = Field(default=Path("knowledge_graph"))

    llm_provider: str = Field(default="ollama")
    llm_base_url: str = Field(default="http://localhost:11434")
    llm_chat_model: str = Field(default="qwen3:8b")
    llm_embed_model: str = Field(default="nomic-embed-text")

    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    def resolve(self, path: Path) -> Path:
        """Resolve relative paths against the repository root."""

        return path if path.is_absolute() else self.project_root / path

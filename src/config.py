"""Global configuration for Enterprise OKF AI project.

Centralizes path resolution, LLM runtime settings, and environment access.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """Runtime configuration loaded from environment variables.

    Example:
        >>> cfg = AppConfig.from_env()
        >>> cfg.okf_output_dir
    """

    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[1])
    data_dir: Path = Field(default_factory=lambda: Path("data"))
    raw_docs_dir: Path = Field(default_factory=lambda: Path("data/raw"))
    artifacts_dir: Path = Field(default_factory=lambda: Path("artifacts"))
    okf_output_dir: Path = Field(default_factory=lambda: Path("okf_bundle"))

    llm_provider: str = "ollama"
    llm_model: str = "qwen3:8b"
    llm_base_url: str = "http://localhost:11434"
    llm_temperature: float = 0.0

    env_name: str = "development"
    log_level: str = "INFO"

    openai_api_key: str | None = None

    @classmethod
    def from_env(cls) -> AppConfig:
        """Create config object from process environment variables."""

        return cls(
            project_root=Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[1])),
            data_dir=Path(os.getenv("DATA_DIR", "data")),
            raw_docs_dir=Path(os.getenv("RAW_DOCS_DIR", "data/raw")),
            artifacts_dir=Path(os.getenv("ARTIFACTS_DIR", "artifacts")),
            okf_output_dir=Path(os.getenv("OKF_OUTPUT_DIR", "okf_bundle")),
            llm_provider=os.getenv("LLM_PROVIDER", "ollama"),
            llm_model=os.getenv("LLM_MODEL", "qwen3:8b"),
            llm_base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434"),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
            env_name=os.getenv("ENV_NAME", "development"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )

    def resolve(self, path: Path) -> Path:
        """Resolve relative paths against the project root."""

        return path if path.is_absolute() else self.project_root / path


config = AppConfig.from_env()

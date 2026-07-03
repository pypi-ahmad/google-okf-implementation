"""Shared typed contracts for scaffold-level orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ServiceResult:
    """Generic service result for command and API responses."""

    status: str
    message: str


@dataclass(slots=True)
class GraphArtifacts:
    """Graph build/export outputs."""

    nodes: int
    edges: int
    json_path: Path
    html_path: Path
    graphml_path: Path | None = None

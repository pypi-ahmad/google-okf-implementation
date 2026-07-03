"""Knowledge graph service wrappers."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import networkx as nx

from enterprise_okf_ai.core.types import GraphArtifacts
from graph.builder import KnowledgeGraphBuilder


class GraphService:
    """Build and export a directed knowledge graph from an OKF bundle."""

    def __init__(self, okf_dir: str | Path):
        self._builder = KnowledgeGraphBuilder(okf_dir)

    def build(self) -> nx.DiGraph:
        """Build in-memory directed graph."""

        return self._builder.build()

    def build_and_export(
        self,
        json_path: str | Path,
        html_path: str | Path,
        graphml_path: str | Path | None = None,
    ) -> GraphArtifacts:
        """Build graph and export JSON, HTML, and optional GraphML artifacts."""

        graph = self._builder.build()
        written_json = self._builder.export_json(json_path)
        written_html = self._builder.export_html(html_path)
        written_graphml = self._builder.export_graphml(graphml_path) if graphml_path is not None else None
        return GraphArtifacts(
            nodes=graph.number_of_nodes(),
            edges=graph.number_of_edges(),
            json_path=written_json,
            html_path=written_html,
            graphml_path=written_graphml,
        )

    def neighbors(
        self,
        concept_id: str,
        depth: int = 1,
        direction: Literal["out", "in", "both"] = "out",
        relation: str | None = None,
    ) -> list[str]:
        """Traverse neighboring concepts from the built graph."""

        return self._builder.neighbors(
            concept_id=concept_id,
            depth=depth,
            direction=direction,
            relation=relation,
        )

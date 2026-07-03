"""Knowledge graph builder for OKF markdown bundles."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import networkx as nx
import yaml
from networkx.readwrite import json_graph
from pyvis.network import Network

LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
RESERVED_FILES = {"index.md", "log.md", "readme.md"}
TraversalDirection = Literal["out", "in", "both"]


@dataclass(slots=True)
class ConceptNode:
    """Structured node metadata extracted from one OKF markdown file."""

    concept_id: str
    path: Path
    title: str
    concept_type: str
    description: str
    tags: list[str]
    resource: str | None
    dependencies: list[str]
    links: list[str]
    relationship_paths: list[str]


class KnowledgeGraphBuilder:
    """Build and traverse directed knowledge graph from OKF bundle markdown."""

    def __init__(self, okf_dir: str | Path):
        self.okf_dir = Path(okf_dir)
        self.graph = nx.DiGraph()

    def build(self) -> nx.DiGraph:
        """Parse markdown files and build a directed graph of relationships."""

        self.graph.clear()
        concept_nodes = self._load_concept_nodes()
        node_by_path = {node.path.resolve(): node for node in concept_nodes}
        node_by_title = {node.title.lower(): node for node in concept_nodes if node.title}
        node_by_id = {node.concept_id: node for node in concept_nodes}

        for node in concept_nodes:
            self.graph.add_node(
                node.concept_id,
                title=node.title,
                type=node.concept_type,
                path=node.path.as_posix(),
                description=node.description,
                tags=node.tags,
                resource=node.resource,
            )

        for node in concept_nodes:
            source_id = node.concept_id

            for raw_link in node.links:
                target = self._resolve_link_target(node=node, raw_link=raw_link, node_by_path=node_by_path)
                if target is None:
                    continue
                self._add_relation_edge(source_id, target.concept_id, relation="markdown_link")

            for raw_link in node.relationship_paths:
                target = self._resolve_link_target(node=node, raw_link=raw_link, node_by_path=node_by_path)
                if target is None:
                    continue
                self._add_relation_edge(source_id, target.concept_id, relation="frontmatter_relationship")

            for dependency in node.dependencies:
                dependency_key = dependency.strip().lower()
                if not dependency_key:
                    continue

                target = node_by_title.get(dependency_key)
                if target is None:
                    target = node_by_id.get(dependency.strip())
                if target is None:
                    target = self._resolve_link_target(node=node, raw_link=dependency, node_by_path=node_by_path)
                if target is None:
                    continue

                self._add_relation_edge(source_id, target.concept_id, relation="dependency")

        return self.graph

    def neighbors(
        self,
        concept_id: str,
        depth: int = 1,
        direction: TraversalDirection = "out",
        relation: str | None = None,
    ) -> list[str]:
        """Return relation-aware neighbors from the in-memory graph."""

        if concept_id not in self.graph:
            return []

        visited: set[str] = {concept_id}
        frontier: set[str] = {concept_id}
        collected: list[str] = []

        for _ in range(max(depth, 0)):
            next_frontier: set[str] = set()
            for node in frontier:
                for candidate in self._adjacent(node=node, direction=direction, relation=relation):
                    if candidate in visited:
                        continue
                    visited.add(candidate)
                    collected.append(candidate)
                    next_frontier.add(candidate)
            frontier = next_frontier
            if not frontier:
                break

        return collected

    def relation_subgraph(
        self,
        concept_id: str,
        depth: int = 2,
        direction: TraversalDirection = "both",
        relation: str | None = None,
    ) -> nx.DiGraph:
        """Return induced subgraph around one concept for retrieval augmentation."""

        nodes = {concept_id}
        nodes.update(self.neighbors(concept_id=concept_id, depth=depth, direction=direction, relation=relation))
        return self.graph.subgraph(nodes).copy()

    def export_json(self, output_path: str | Path) -> Path:
        """Export current graph to node-link JSON."""

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        data = json_graph.node_link_data(self.graph, edges="links")
        output.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return output

    def export_graphml(self, output_path: str | Path) -> Path:
        """Export current graph to GraphML format."""

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        export_graph = nx.DiGraph()
        for node_id, attrs in self.graph.nodes(data=True):
            normalized = {key: self._to_graphml_value(value) for key, value in attrs.items()}
            export_graph.add_node(node_id, **normalized)

        for source, target, attrs in self.graph.edges(data=True):
            normalized = {key: self._to_graphml_value(value) for key, value in attrs.items()}
            export_graph.add_edge(source, target, **normalized)

        nx.write_graphml(export_graph, output)
        return output

    def export_html(self, output_path: str | Path) -> Path:
        """Export graph to interactive HTML using pyvis."""

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        net = Network(height="900px", width="100%", directed=True, bgcolor="#ffffff", font_color="#111827")

        for node_id, attrs in self.graph.nodes(data=True):
            title = attrs.get("title", node_id)
            node_type = attrs.get("type", "concept")
            net.add_node(
                node_id,
                label=title,
                title=f"type: {node_type}<br>path: {attrs.get('path', '')}",
                group=node_type,
            )

        for source, target, attrs in self.graph.edges(data=True):
            relation = attrs.get("relation", "related_to")
            net.add_edge(source, target, title=relation, label=relation)

        net.save_graph(str(output))
        return output

    def _adjacent(self, node: str, direction: TraversalDirection, relation: str | None) -> list[str]:
        neighbors: list[str] = []

        if direction in {"out", "both"}:
            for _, target, attrs in self.graph.out_edges(node, data=True):
                if self._matches_relation(attrs, relation):
                    neighbors.append(target)

        if direction in {"in", "both"}:
            for source, _, attrs in self.graph.in_edges(node, data=True):
                if self._matches_relation(attrs, relation):
                    neighbors.append(source)

        return neighbors

    def _add_relation_edge(self, source: str, target: str, relation: str) -> None:
        if not self.graph.has_edge(source, target):
            self.graph.add_edge(source, target, relation=relation, relations=[relation])
            return

        attrs = self.graph[source][target]
        existing = attrs.get("relations")
        relations = (
            {str(item) for item in existing}
            if isinstance(existing, list)
            else {str(attrs.get("relation", relation))}
        )

        relations.add(relation)
        attrs["relations"] = sorted(relations)
        if "relation" not in attrs or not attrs["relation"]:
            attrs["relation"] = relation

    def _matches_relation(self, attrs: dict[str, Any], relation: str | None) -> bool:
        if relation is None:
            return True

        relations = attrs.get("relations")
        if isinstance(relations, list):
            return relation in {str(item) for item in relations}

        return str(attrs.get("relation", "")) == relation

    def _load_concept_nodes(self) -> list[ConceptNode]:
        if not self.okf_dir.exists() or not self.okf_dir.is_dir():
            raise FileNotFoundError(f"OKF directory not found: {self.okf_dir}")

        nodes: list[ConceptNode] = []
        for path in sorted(self.okf_dir.rglob("*.md")):
            if not path.is_file() or path.name.lower() in RESERVED_FILES:
                continue

            frontmatter, body = self._parse_frontmatter(path)
            rel_path = path.resolve().relative_to(self.okf_dir.resolve()).as_posix()
            concept_id = str(frontmatter.get("id", "")).strip() or (rel_path[:-3] if rel_path.endswith(".md") else rel_path)

            tags = frontmatter.get("tags", [])
            dependencies = frontmatter.get("dependencies", [])
            relationships = frontmatter.get("relationships", [])

            if not isinstance(tags, list):
                tags = []
            if not isinstance(dependencies, list):
                dependencies = []

            relationship_paths: list[str] = []
            if isinstance(relationships, list):
                for item in relationships:
                    if isinstance(item, dict):
                        value = item.get("path")
                        if isinstance(value, str) and value.strip():
                            relationship_paths.append(value.strip())
                    elif isinstance(item, str) and item.strip():
                        relationship_paths.append(item.strip())

            nodes.append(
                ConceptNode(
                    concept_id=concept_id,
                    path=path,
                    title=str(frontmatter.get("title", concept_id)),
                    concept_type=str(frontmatter.get("type", "concept")),
                    description=str(frontmatter.get("description", "")),
                    tags=[str(tag) for tag in tags],
                    resource=str(frontmatter.get("resource")) if frontmatter.get("resource") is not None else None,
                    dependencies=[str(dep) for dep in dependencies],
                    links=[match.strip() for match in LINK_PATTERN.findall(body) if match.strip()],
                    relationship_paths=relationship_paths,
                )
            )

        return nodes

    def _parse_frontmatter(self, path: Path) -> tuple[dict[str, Any], str]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()

        if not lines or lines[0].strip() != "---":
            return {}, text

        end_idx = None
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                end_idx = index
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

    def _resolve_link_target(
        self,
        node: ConceptNode,
        raw_link: str,
        node_by_path: dict[Path, ConceptNode],
    ) -> ConceptNode | None:
        normalized = raw_link.strip()
        if not normalized or normalized.startswith(("http://", "https://", "mailto:", "#")):
            return None

        normalized = normalized.split("#", 1)[0].split("?", 1)[0].strip()
        if not normalized:
            return None

        if normalized.startswith("/"):
            base_candidates = [self.okf_dir / normalized.lstrip("/")]
        else:
            base_candidates = [node.path.parent / normalized, self.okf_dir / normalized]

        options: list[Path] = []
        for candidate in base_candidates:
            options.append(candidate)
            if candidate.suffix == "":
                options.append(candidate.with_suffix(".md"))

        for option in options:
            try:
                resolved = option.resolve()
            except OSError:
                continue
            if resolved in node_by_path:
                return node_by_path[resolved]

        return None

    def _to_graphml_value(self, value: Any) -> str | int | float | bool:
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, list):
            return ",".join(str(item) for item in value)
        if value is None:
            return ""
        return str(value)

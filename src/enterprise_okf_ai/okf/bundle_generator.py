"""Deterministic OKF bundle generator from normalized enterprise documents."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml
from loguru import logger

from ingest.parser import ParsedDocument

ConceptType = Literal["dataset", "api", "metric", "playbook", "table", "glossary"]

OKF_DIRECTORIES: dict[ConceptType, str] = {
    "dataset": "datasets",
    "api": "apis",
    "metric": "metrics",
    "playbook": "playbooks",
    "table": "tables",
    "glossary": "glossary",
}

_REQUIRED_FRONTMATTER_KEYS = {
    "id",
    "type",
    "title",
    "description",
    "tags",
    "resource",
    "sources",
    "relationships",
    "timestamp",
}

_GENERIC_PATH_TOKENS = {
    "data",
    "docs",
    "documentation",
    "raw",
    "input",
    "src",
    "knowledge",
    "enterprise",
}


@dataclass(slots=True)
class ConceptRelationship:
    """Relationship between two OKF knowledge objects."""

    relationship_type: str
    target_id: str
    target_type: ConceptType
    target_title: str
    path: str

    def to_dict(self) -> dict[str, str]:
        """Serialize relationship for YAML frontmatter."""

        return {
            "type": self.relationship_type,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "target_title": self.target_title,
            "path": self.path,
        }


@dataclass(slots=True)
class KnowledgeObject:
    """Canonical OKF concept persisted as markdown + frontmatter."""

    object_id: str
    concept_type: ConceptType
    slug: str
    title: str
    description: str
    tags: list[str]
    resource: str
    sources: list[str]
    timestamp: str
    notes: list[str]
    related_titles: list[str]
    relationships: list[ConceptRelationship] = field(default_factory=list)

    @property
    def relative_path(self) -> str:
        """OKF-relative markdown path for this object."""

        folder = OKF_DIRECTORIES[self.concept_type]
        return f"{folder}/{self.slug}.md"


@dataclass(slots=True)
class BundleBuildReport:
    """Summary of one OKF bundle build run."""

    output_dir: Path
    source_dir: Path
    concept_count: int
    deduplicated_concepts: int
    concepts_by_type: dict[str, int]
    files_written: list[Path]

    def to_dict(self) -> dict[str, object]:
        """Serialize report into JSON-friendly structure."""

        return {
            "output_dir": self.output_dir.as_posix(),
            "source_dir": self.source_dir.as_posix(),
            "concept_count": self.concept_count,
            "deduplicated_concepts": self.deduplicated_concepts,
            "concepts_by_type": self.concepts_by_type,
            "files_written": [path.as_posix() for path in self.files_written],
        }


@dataclass(slots=True)
class _ConceptCandidate:
    concept_type: ConceptType
    title: str
    description: str
    tags: set[str]
    resource: str
    sources: set[str]
    timestamp: str
    related_titles: set[str]
    notes: list[str]


@dataclass(slots=True)
class _ConceptAccumulator:
    concept_type: ConceptType
    title: str
    slug: str
    description: str
    tags: set[str] = field(default_factory=set)
    resource: str = ""
    sources: set[str] = field(default_factory=set)
    timestamps: list[str] = field(default_factory=list)
    related_titles: set[str] = field(default_factory=set)
    notes: list[str] = field(default_factory=list)


class OKFBundleGenerator:
    """Generate strict OKF-style markdown bundles from parsed enterprise documents."""

    def __init__(self, output_dir: str | Path, source_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.source_dir = Path(source_dir)

    def build(self, documents: list[ParsedDocument]) -> BundleBuildReport:
        """Build OKF bundle from normalized ingestion documents."""

        logger.info("Building OKF bundle from {} parsed documents", len(documents))
        candidates = self._collect_candidates(documents)
        concepts, dedup_count = self._deduplicate(candidates)
        self._resolve_relationships(concepts)

        files_written = self._write_bundle(concepts)
        concepts_by_type = self._count_by_type(concepts)

        report = BundleBuildReport(
            output_dir=self.output_dir,
            source_dir=self.source_dir,
            concept_count=len(concepts),
            deduplicated_concepts=dedup_count,
            concepts_by_type=concepts_by_type,
            files_written=files_written,
        )
        logger.info("OKF bundle build complete: {} concepts", report.concept_count)
        return report

    def _collect_candidates(self, documents: list[ParsedDocument]) -> list[_ConceptCandidate]:
        candidates: list[_ConceptCandidate] = []

        for document in sorted(documents, key=lambda doc: doc.file_path.as_posix()):
            doc_candidates = self._extract_candidates_from_document(document)
            candidates.extend(doc_candidates)

        return candidates

    def _extract_candidates_from_document(self, document: ParsedDocument) -> list[_ConceptCandidate]:
        concept_type = self._infer_concept_type(document)
        resource = self._relative_source_path(document.file_path)
        timestamp = self._select_timestamp(document)

        if concept_type == "glossary":
            glossary_entries = self._extract_glossary_entries(document)
            if glossary_entries:
                candidates: list[_ConceptCandidate] = []
                for term, definition in glossary_entries:
                    tags = self._derive_tags(document, concept_type)
                    tags.add("glossary")
                    candidates.append(
                        _ConceptCandidate(
                            concept_type="glossary",
                            title=term,
                            description=definition,
                            tags=tags,
                            resource=resource,
                            sources={resource},
                            timestamp=timestamp,
                            related_titles=self._extract_relationship_titles(document.content),
                            notes=self._build_notes(document),
                        )
                    )
                return candidates

        title = self._derive_title(document, concept_type)
        description = self._derive_description(document)

        return [
            _ConceptCandidate(
                concept_type=concept_type,
                title=title,
                description=description,
                tags=self._derive_tags(document, concept_type),
                resource=resource,
                sources={resource},
                timestamp=timestamp,
                related_titles=self._extract_relationship_titles(document.content),
                notes=self._build_notes(document),
            )
        ]

    def _infer_concept_type(self, document: ParsedDocument) -> ConceptType:
        path_tokens = {token.lower() for token in document.file_path.parts}
        path_string = document.file_path.as_posix().lower()
        content = document.content.lower()

        # Path-driven typing is strict and takes precedence over content heuristics.
        if "glossary" in path_tokens or "glossary" in path_string:
            return "glossary"
        if "api" in path_tokens or "apis" in path_tokens:
            return "api"
        if "metrics" in path_tokens or "metric" in path_tokens:
            return "metric"
        if document.file_type == "csv" or "tables" in path_tokens or "table" in path_tokens:
            return "table"
        if any(token in path_tokens for token in {"schema", "data_dictionary", "dictionary"}):
            return "table"
        if "datasets" in path_tokens or "dataset" in path_tokens:
            return "dataset"
        if any(token in path_tokens for token in {"runbooks", "runbook", "playbook", "playbooks", "incidents"}):
            return "playbook"

        # Content-driven fallback for unstructured locations.
        if "runbook" in content or "playbook" in content:
            return "playbook"
        if re.search(r"\b(get|post|put|patch|delete)\s+/", content):
            return "api"
        if re.search(r"\b(kpi|metric|monthly active users|mau|formula)\b", content):
            return "metric"
        if document.tables:
            return "table"

        return "dataset"

    def _derive_title(self, document: ParsedDocument, concept_type: ConceptType) -> str:
        if document.headings:
            candidate = document.headings[0].text.strip()
            if candidate:
                return candidate

        stem = document.file_path.stem.replace("_", " ").replace("-", " ").strip()
        title = re.sub(r"\s+", " ", stem).title()
        if title:
            return title

        return f"{concept_type.title()} Concept"

    def _derive_description(self, document: ParsedDocument) -> str:
        lines = [line.strip() for line in document.content.splitlines()]
        candidate_lines = [line for line in lines if line and not line.startswith("#")]

        if candidate_lines:
            first_line = re.sub(r"\s+", " ", candidate_lines[0])
            if len(first_line) > 300:
                return first_line[:297].rstrip() + "..."
            return first_line

        if document.headings:
            return f"Knowledge object derived from {document.headings[0].text.strip()}."

        return "Knowledge object extracted from enterprise documentation."

    def _derive_tags(self, document: ParsedDocument, concept_type: ConceptType) -> set[str]:
        tags = {concept_type, document.file_type}

        for part in document.file_path.parent.parts:
            token = re.sub(r"[^a-zA-Z0-9]+", "-", part.lower()).strip("-")
            if not token or token in _GENERIC_PATH_TOKENS:
                continue
            tags.add(token)

        return {tag for tag in tags if tag}

    def _extract_glossary_entries(self, document: ParsedDocument) -> list[tuple[str, str]]:
        entries: list[tuple[str, str]] = []

        for table in document.tables:
            lowered_headers = [header.lower().strip() for header in table.headers]
            if "term" in lowered_headers and "definition" in lowered_headers:
                term_index = lowered_headers.index("term")
                def_index = lowered_headers.index("definition")
                for row in table.rows:
                    if term_index >= len(row) or def_index >= len(row):
                        continue
                    term = row[term_index].strip()
                    definition = row[def_index].strip()
                    if term and definition:
                        entries.append((term, definition))

        for line in document.content.splitlines():
            match = re.match(r"^\s*[-*]\s*([^:]{2,80}?)\s*:\s*(.+)$", line.strip())
            if not match:
                continue
            term = match.group(1).strip()
            definition = match.group(2).strip()
            if term and definition:
                entries.append((term, definition))

        deduplicated: dict[str, str] = {}
        for term, definition in entries:
            key = self._normalize_text_key(term)
            current = deduplicated.get(key)
            if current is None or len(definition) > len(current):
                deduplicated[key] = definition

        return sorted((self._title_case_from_key(key), value) for key, value in deduplicated.items())

    def _extract_relationship_titles(self, content: str) -> set[str]:
        titles: set[str] = set()

        for token in re.findall(r"`([^`]{2,120})`", content):
            cleaned = token.strip()
            if cleaned:
                titles.add(cleaned)

        for line in content.splitlines():
            stripped = line.strip()
            bullet_match = re.match(r"^[-*]\s+(.+)$", stripped)
            if bullet_match:
                candidate = bullet_match.group(1).strip()
                candidate = re.sub(r"\(.*?\)", "", candidate).strip()
                if 2 <= len(candidate) <= 120 and not candidate.lower().startswith("http"):
                    titles.add(candidate)

        return {title for title in titles if title}

    def _build_notes(self, document: ParsedDocument) -> list[str]:
        notes: list[str] = []
        for section in document.sections[:4]:
            snippet = section.content.strip()
            if not snippet:
                continue
            if len(snippet) > 900:
                snippet = snippet[:897].rstrip() + "..."
            notes.append(snippet)

        if not notes and document.content.strip():
            snippet = document.content.strip()
            if len(snippet) > 900:
                snippet = snippet[:897].rstrip() + "..."
            notes.append(snippet)

        return notes

    def _deduplicate(self, candidates: list[_ConceptCandidate]) -> tuple[list[KnowledgeObject], int]:
        accumulators: dict[tuple[ConceptType, str], _ConceptAccumulator] = {}
        dedup_count = 0

        for candidate in sorted(candidates, key=lambda item: (item.concept_type, self._slugify(item.title), item.resource)):
            slug = self._slugify(candidate.title)
            key = (candidate.concept_type, slug)
            existing = accumulators.get(key)

            if existing is None:
                accumulators[key] = _ConceptAccumulator(
                    concept_type=candidate.concept_type,
                    title=candidate.title,
                    slug=slug,
                    description=candidate.description,
                    tags=set(candidate.tags),
                    resource=candidate.resource,
                    sources=set(candidate.sources),
                    timestamps=[candidate.timestamp],
                    related_titles=set(candidate.related_titles),
                    notes=list(candidate.notes),
                )
                continue

            dedup_count += 1
            if len(candidate.description) > len(existing.description):
                existing.description = candidate.description

            existing.tags.update(candidate.tags)
            existing.sources.update(candidate.sources)
            existing.related_titles.update(candidate.related_titles)
            existing.notes.extend(candidate.notes)
            existing.timestamps.append(candidate.timestamp)

            if candidate.resource < existing.resource:
                existing.resource = candidate.resource

        concepts: list[KnowledgeObject] = []
        for (concept_type, slug), accumulator in sorted(accumulators.items(), key=lambda item: (item[0][0], item[0][1])):
            object_id = f"{concept_type}:{slug}"
            timestamp = self._canonical_timestamp(accumulator.timestamps)
            notes = self._dedupe_ordered(accumulator.notes)
            concepts.append(
                KnowledgeObject(
                    object_id=object_id,
                    concept_type=concept_type,
                    slug=slug,
                    title=accumulator.title,
                    description=accumulator.description,
                    tags=sorted(accumulator.tags),
                    resource=accumulator.resource,
                    sources=sorted(accumulator.sources),
                    timestamp=timestamp,
                    notes=notes,
                    related_titles=sorted(accumulator.related_titles),
                )
            )

        return concepts, dedup_count

    def _resolve_relationships(self, concepts: list[KnowledgeObject]) -> None:
        if not concepts:
            return

        ordered_concepts = sorted(concepts, key=self._concept_order_key)
        by_id = {concept.object_id: concept for concept in ordered_concepts}
        normalized_title_index = {
            self._normalize_text_key(concept.title): concept.object_id
            for concept in ordered_concepts
        }
        order_index = {
            concept.object_id: idx
            for idx, concept in enumerate(ordered_concepts)
        }

        undirected_pairs: set[tuple[str, str]] = set()
        for concept in ordered_concepts:
            joined_notes = "\n".join(concept.notes).lower()

            for other in ordered_concepts:
                if other.object_id == concept.object_id:
                    continue
                other_title = other.title.lower().strip()
                if other_title and other_title in joined_notes:
                    pair = (
                        (concept.object_id, other.object_id)
                        if concept.object_id < other.object_id
                        else (other.object_id, concept.object_id)
                    )
                    undirected_pairs.add(pair)

            for related_title in concept.related_titles:
                target_id = normalized_title_index.get(self._normalize_text_key(related_title))
                if target_id is None or target_id == concept.object_id:
                    continue
                pair = (
                    (concept.object_id, target_id)
                    if concept.object_id < target_id
                    else (target_id, concept.object_id)
                )
                undirected_pairs.add(pair)

        adjacency: dict[str, set[str]] = {concept.object_id: set() for concept in ordered_concepts}
        for left_id, right_id in sorted(undirected_pairs):
            left_order = order_index[left_id]
            right_order = order_index[right_id]
            source_id = left_id if left_order < right_order else right_id
            target_id = right_id if source_id == left_id else left_id
            adjacency[source_id].add(target_id)

        inbound_counts: dict[str, int] = {concept.object_id: 0 for concept in ordered_concepts}
        for source_id, outbound_targets in adjacency.items():
            for target_id in outbound_targets:
                inbound_counts[target_id] += 1

        for concept in ordered_concepts:
            concept_id = concept.object_id
            has_outbound = bool(adjacency[concept_id])
            has_inbound = inbound_counts[concept_id] > 0
            if has_outbound or has_inbound:
                continue

            anchor = self._fallback_relationship_target(concept, ordered_concepts, order_index)
            if anchor is None:
                continue

            if order_index[concept_id] < order_index[anchor.object_id]:
                source_id = concept_id
                target_id = anchor.object_id
            else:
                source_id = anchor.object_id
                target_id = concept_id

            if target_id not in adjacency[source_id]:
                adjacency[source_id].add(target_id)
                inbound_counts[target_id] += 1

        for concept in ordered_concepts:
            sorted_target_ids = sorted(adjacency[concept.object_id], key=lambda concept_id: order_index[concept_id])
            concept.relationships = [self._relationship_for(concept, by_id[target_id]) for target_id in sorted_target_ids]

    def _fallback_relationship_target(
        self,
        concept: KnowledgeObject,
        concepts: list[KnowledgeObject],
        order_index: dict[str, int],
    ) -> KnowledgeObject | None:
        for candidate in concepts:
            if candidate.object_id == concept.object_id:
                continue
            if candidate.concept_type == concept.concept_type:
                return candidate

        neighbors: list[KnowledgeObject] = [
            candidate
            for candidate in concepts
            if candidate.object_id != concept.object_id
        ]
        if not neighbors:
            return None

        current_order = order_index[concept.object_id]
        return min(
            neighbors,
            key=lambda candidate: abs(order_index[candidate.object_id] - current_order),
        )

    def _relationship_for(self, source: KnowledgeObject, target: KnowledgeObject) -> ConceptRelationship:
        return ConceptRelationship(
            relationship_type="references",
            target_id=target.object_id,
            target_type=target.concept_type,
            target_title=target.title,
            path=target.relative_path,
        )

    def _write_bundle(self, concepts: list[KnowledgeObject]) -> list[Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for folder in OKF_DIRECTORIES.values():
            folder_path = self.output_dir / folder
            folder_path.mkdir(parents=True, exist_ok=True)
            for existing in folder_path.glob("*.md"):
                existing.unlink()

        files_written: list[Path] = []
        for concept in concepts:
            folder = OKF_DIRECTORIES[concept.concept_type]
            file_path = self.output_dir / folder / f"{concept.slug}.md"
            content = self._render_markdown(concept)
            file_path.write_text(content, encoding="utf-8")
            files_written.append(file_path)

        index_path = self._write_index(concepts)
        manifest_path = self._write_manifest(concepts)
        files_written.extend([index_path, manifest_path])
        return files_written

    def _render_markdown(self, concept: KnowledgeObject) -> str:
        frontmatter: dict[str, object] = {
            "id": concept.object_id,
            "type": concept.concept_type,
            "title": concept.title,
            "description": concept.description,
            "tags": concept.tags,
            "resource": concept.resource,
            "sources": concept.sources,
            "relationships": [relationship.to_dict() for relationship in concept.relationships],
            "timestamp": concept.timestamp,
        }
        self._validate_frontmatter(frontmatter)

        yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=False).strip()
        body_lines: list[str] = [
            f"# {concept.title}",
            "",
            "## Summary",
            concept.description,
            "",
            "## Source References",
        ]

        for source in concept.sources:
            body_lines.append(f"- `{source}`")

        body_lines.extend(["", "## Tags"])
        if concept.tags:
            body_lines.append(", ".join(f"`{tag}`" for tag in concept.tags))
        else:
            body_lines.append("none")

        body_lines.extend(["", "## Relationships"])
        if concept.relationships:
            for relationship in concept.relationships:
                relative_link = self._relationship_markdown_path(concept, relationship)
                body_lines.append(
                    f"- [{relationship.target_title}]({relative_link}) "
                    f"(`{relationship.target_id}`, type=`{relationship.target_type}`)"
                )
        else:
            body_lines.append("- none")

        body_lines.extend(["", "## Knowledge Notes"])
        if concept.notes:
            for index, note in enumerate(concept.notes, start=1):
                body_lines.append(f"### Excerpt {index}")
                body_lines.append(note)
                body_lines.append("")
        else:
            body_lines.append("No source excerpt available.")

        markdown_body = "\n".join(body_lines).rstrip() + "\n"
        return f"---\n{yaml_text}\n---\n\n{markdown_body}"

    def _relationship_markdown_path(self, source: KnowledgeObject, relationship: ConceptRelationship) -> str:
        source_folder = Path(OKF_DIRECTORIES[source.concept_type])
        target_path = Path(relationship.path)
        relative = Path("..") / target_path if source_folder != target_path.parent else Path(target_path.name)
        return relative.as_posix()

    def _write_index(self, concepts: list[KnowledgeObject]) -> Path:
        lines = [
            "# OKF Knowledge Bundle",
            "",
            "Portable enterprise knowledge bundle in markdown + YAML frontmatter.",
            "",
            "## Structure",
        ]

        for concept_type, folder in OKF_DIRECTORIES.items():
            count = sum(1 for concept in concepts if concept.concept_type == concept_type)
            lines.append(f"- `{folder}/`: {count} objects")

        lines.extend(["", "## Concepts"])
        for concept in concepts:
            lines.append(f"- [{concept.title}]({concept.relative_path}) - `{concept.object_id}`")

        index_path = self.output_dir / "README.md"
        index_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return index_path

    def _write_manifest(self, concepts: list[KnowledgeObject]) -> Path:
        manifest = {
            "okf_style_version": "0.1",
            "source_root": self.source_dir.as_posix(),
            "concept_count": len(concepts),
            "concepts": [
                {
                    "id": concept.object_id,
                    "type": concept.concept_type,
                    "title": concept.title,
                    "path": concept.relative_path,
                }
                for concept in concepts
            ],
        }

        manifest_path = self.output_dir / "bundle_manifest.yaml"
        manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=False), encoding="utf-8")
        return manifest_path

    def _validate_frontmatter(self, frontmatter: dict[str, object]) -> None:
        missing = sorted(_REQUIRED_FRONTMATTER_KEYS - set(frontmatter.keys()))
        if missing:
            raise ValueError(f"Missing mandatory frontmatter fields: {missing}")

        title = str(frontmatter.get("title", "")).strip()
        description = str(frontmatter.get("description", "")).strip()
        if not title:
            raise ValueError("Frontmatter field `title` cannot be empty")
        if not description:
            raise ValueError("Frontmatter field `description` cannot be empty")

        serialized = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=False)
        loaded = yaml.safe_load(serialized)
        if not isinstance(loaded, dict):
            raise ValueError("Frontmatter serialization is not valid YAML mapping")

    def _count_by_type(self, concepts: list[KnowledgeObject]) -> dict[str, int]:
        counts: dict[str, int] = {concept_type: 0 for concept_type in OKF_DIRECTORIES}
        for concept in concepts:
            counts[concept.concept_type] += 1
        return counts

    def _relative_source_path(self, path: Path) -> str:
        try:
            return path.relative_to(self.source_dir).as_posix()
        except ValueError:
            return path.as_posix()

    def _select_timestamp(self, document: ParsedDocument) -> str:
        candidate = document.metadata.get("creation_date") or document.metadata.get("modified_date")
        if candidate:
            return str(candidate)
        return "1970-01-01T00:00:00+00:00"

    def _canonical_timestamp(self, timestamps: list[str]) -> str:
        normalized = [timestamp for timestamp in timestamps if timestamp]
        if not normalized:
            return "1970-01-01T00:00:00+00:00"

        def sort_key(value: str) -> tuple[int, datetime | str]:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return (0, parsed)
            except ValueError:
                return (1, value)

        best = min(normalized, key=sort_key)
        return best

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
        return slug or "untitled"

    def _normalize_text_key(self, value: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9]+", " ", value.lower()).strip()
        return re.sub(r"\s+", " ", normalized)

    def _concept_order_key(self, concept: KnowledgeObject) -> tuple[int, str, str]:
        type_rank = {
            "dataset": 0,
            "table": 1,
            "api": 2,
            "metric": 3,
            "playbook": 4,
            "glossary": 5,
        }
        return (
            type_rank.get(concept.concept_type, 99),
            concept.slug,
            concept.object_id,
        )

    def _title_case_from_key(self, key: str) -> str:
        return " ".join(part.capitalize() for part in key.split())

    def _dedupe_ordered(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            normalized = value.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            ordered.append(normalized)
        return ordered

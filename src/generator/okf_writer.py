"""Strict OKF v0.1 markdown writer."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from extractor.schema import (
    APIConcept,
    DatasetConcept,
    EnterpriseConcepts,
    EntityConcept,
    GlossaryTermConcept,
    MetricConcept,
    TableConcept,
)

REQUIRED_FRONTMATTER_KEYS = ["type", "title", "description", "tags", "resource", "timestamp"]


class OKFWriter:
    """Generate strict OKF v0.1 bundle structure from extracted concepts.

    Example:
        >>> writer = OKFWriter(Path("okf_bundle"))
        >>> writer.write(concepts=concepts, source_text="...", resource="docs/api.md")
    """

    def __init__(self, target_dir: str | Path):
        self.target_dir = Path(target_dir)

    def write(self, concepts: EnterpriseConcepts, source_text: str, resource: str) -> list[Path]:
        """Materialize concept files as markdown + YAML frontmatter."""

        self._ensure_structure()
        generated: list[Path] = []
        timestamp = datetime.now(timezone.utc).isoformat()

        generated.extend(
            self._write_group(
                folder="entities",
                concept_type="entity",
                entries=concepts.entities,
                source_text=source_text,
                resource=resource,
                timestamp=timestamp,
            )
        )
        generated.extend(
            self._write_group(
                folder="datasets",
                concept_type="dataset",
                entries=concepts.datasets,
                source_text=source_text,
                resource=resource,
                timestamp=timestamp,
            )
        )
        generated.extend(
            self._write_group(
                folder="apis",
                concept_type="api",
                entries=concepts.apis,
                source_text=source_text,
                resource=resource,
                timestamp=timestamp,
            )
        )
        generated.extend(
            self._write_group(
                folder="tables",
                concept_type="table",
                entries=concepts.tables,
                source_text=source_text,
                resource=resource,
                timestamp=timestamp,
            )
        )
        generated.extend(
            self._write_group(
                folder="metrics",
                concept_type="metric",
                entries=concepts.metrics,
                source_text=source_text,
                resource=resource,
                timestamp=timestamp,
            )
        )
        generated.extend(
            self._write_group(
                folder="glossary",
                concept_type="glossary_term",
                entries=concepts.glossary_terms,
                source_text=source_text,
                resource=resource,
                timestamp=timestamp,
            )
        )

        return generated

    def _ensure_structure(self) -> None:
        for folder in ["entities", "datasets", "apis", "tables", "metrics", "glossary"]:
            (self.target_dir / folder).mkdir(parents=True, exist_ok=True)

    def _write_group(
        self,
        folder: str,
        concept_type: str,
        entries: list[EntityConcept | DatasetConcept | APIConcept | TableConcept | MetricConcept | GlossaryTermConcept],
        source_text: str,
        resource: str,
        timestamp: str,
    ) -> list[Path]:
        generated: list[Path] = []
        directory = self.target_dir / folder

        for concept in entries:
            title, description, tags = self._concept_core(concept)
            frontmatter = {
                "type": concept_type,
                "title": title,
                "description": description,
                "tags": tags,
                "resource": resource,
                "timestamp": timestamp,
            }
            self._validate_frontmatter(frontmatter)

            markdown = self._to_markdown(frontmatter=frontmatter, concept=concept, source_text=source_text)
            slug = self._slugify(title)
            path = directory / f"{slug}.md"
            path.write_text(markdown, encoding="utf-8")
            generated.append(path)

        return generated

    def _to_markdown(self, frontmatter: dict[str, Any], concept: Any, source_text: str) -> str:
        yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=False).strip()
        # Validate YAML syntax post-serialization.
        loaded = yaml.safe_load(yaml_text)
        if not isinstance(loaded, dict):
            raise ValueError("Generated YAML frontmatter is invalid")

        details = concept.model_dump() if hasattr(concept, "model_dump") else dict(concept)
        detail_lines = []
        for key, value in details.items():
            if key in {"description", "tags"}:
                continue
            detail_lines.append(f"- **{key}**: {value}")

        preview = source_text.strip()[:1200]

        body = [
            "# Summary",
            str(frontmatter["description"]),
            "",
            "# Details",
            *(detail_lines if detail_lines else ["- None"]),
            "",
            "# Source Excerpt",
            preview if preview else "No source excerpt available.",
        ]

        return f"---\n{yaml_text}\n---\n\n" + "\n".join(body).strip() + "\n"

    def _validate_frontmatter(self, frontmatter: dict[str, Any]) -> None:
        missing = [key for key in REQUIRED_FRONTMATTER_KEYS if key not in frontmatter]
        if missing:
            raise ValueError(f"Missing required OKF frontmatter keys: {missing}")

        if not frontmatter["title"] or not str(frontmatter["title"]).strip():
            raise ValueError("OKF frontmatter `title` cannot be empty")
        if not frontmatter["description"] or not str(frontmatter["description"]).strip():
            raise ValueError("OKF frontmatter `description` cannot be empty")

        # YAML round-trip validation.
        serialized = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=False)
        loaded = yaml.safe_load(serialized)
        if not isinstance(loaded, dict):
            raise ValueError("Frontmatter failed YAML validation")

    def _concept_core(self, concept: Any) -> tuple[str, str, list[str]]:
        if isinstance(concept, GlossaryTermConcept):
            return concept.term, concept.definition, concept.tags
        return concept.name, concept.description, concept.tags

    def _slugify(self, value: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
        return normalized or "untitled"

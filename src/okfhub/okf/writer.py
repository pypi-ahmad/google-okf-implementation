"""OKF bundle writer for extracted concept materialization."""

from collections import defaultdict
from pathlib import Path

import yaml
from loguru import logger

from okfhub.models import ConceptDocument, ConceptFrontmatter, ExtractedConcept
from okfhub.utils.filesystem import ensure_dir
from okfhub.utils.okf import concept_slug, iso_now

TYPE_DIRECTORY_MAP = {
    "dataset": "datasets",
    "metric": "metrics",
    "api": "apis",
    "table": "tables",
    "playbook": "playbooks",
    "service": "services",
    "entity": "entities",
    "owner": "owners",
    "glossary": "glossary",
    "dependency": "dependencies",
}


class OKFBundleGenerator:
    """Generate OKF markdown bundle from extracted concepts."""

    def __init__(self, root: Path):
        self._root = root

    def generate(self, concepts: list[ExtractedConcept]) -> list[ConceptDocument]:
        """Write concepts to OKF-compliant markdown files.

        Args:
            concepts: Extracted concept entities.

        Returns:
            Generated concept document metadata.
        """

        ensure_dir(self._root)

        by_id = {concept.concept_id: concept for concept in concepts}
        generated: list[ConceptDocument] = []

        folder_counts: dict[str, int] = defaultdict(int)
        for concept in concepts:
            folder = TYPE_DIRECTORY_MAP.get(concept.concept_type, "concepts")
            folder_counts[folder] += 1
            target_dir = self._root / folder
            ensure_dir(target_dir)

            filename = f"{concept_slug(concept.title)}.md"
            path = target_dir / filename

            frontmatter = ConceptFrontmatter(
                type=concept.concept_type,
                title=concept.title,
                description=concept.description,
                tags=sorted(set(concept.tags)),
                resource=concept.resource,
                timestamp=iso_now(),
            )

            body = self._render_body(concept, by_id)
            serialized = self._serialize(frontmatter, body)
            path.write_text(serialized, encoding="utf-8")

            generated.append(
                ConceptDocument(
                    concept_id=concept.concept_id,
                    relative_path=path.relative_to(self._root).as_posix(),
                    frontmatter=frontmatter,
                    body=body,
                    links=self._extract_links(concept, by_id),
                )
            )

        self._write_index(folder_counts)
        self._append_log_entry(concepts_count=len(generated))

        logger.info("Wrote {} OKF concept files to {}", len(generated), self._root)
        return generated

    def _render_body(self, concept: ExtractedConcept, by_id: dict[str, ExtractedConcept]) -> str:
        lines = [
            "# Summary",
            concept.description,
            "",
            "# Metadata",
            f"- Owners: {', '.join(concept.owners) if concept.owners else 'unknown'}",
            f"- Aliases: {', '.join(concept.aliases) if concept.aliases else 'none'}",
            "",
            "# Dependencies",
        ]

        links = self._extract_links(concept, by_id)
        if links:
            lines.extend(f"- {link}" for link in links)
        else:
            lines.append("- none")

        lines.extend(["", "# Citations", f"- {concept.resource or 'n/a'}"])
        return "\n".join(lines)

    def _extract_links(self, concept: ExtractedConcept, by_id: dict[str, ExtractedConcept]) -> list[str]:
        links: list[str] = []
        for dependency in concept.dependencies:
            dep_obj = by_id.get(dependency)
            if dep_obj is not None:
                dep_folder = TYPE_DIRECTORY_MAP.get(dep_obj.concept_type, "concepts")
                dep_path = f"/{dep_folder}/{concept_slug(dep_obj.title)}.md"
                links.append(f"[{dep_obj.title}]({dep_path})")
            else:
                links.append(f"[{dependency}]({dependency})")
        return links

    def _serialize(self, frontmatter: ConceptFrontmatter, body: str) -> str:
        meta = yaml.safe_dump(frontmatter.model_dump(), sort_keys=False, allow_unicode=False).strip()
        return f"---\n{meta}\n---\n\n{body}\n"

    def _write_index(self, folder_counts: dict[str, int]) -> None:
        lines = ["# OKF Bundle Index", "", "## Directories"]
        for folder, count in sorted(folder_counts.items()):
            lines.append(f"- `{folder}/`: {count} concepts")
        (self._root / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _append_log_entry(self, concepts_count: int) -> None:
        log_path = self._root / "log.md"
        existing = log_path.read_text(encoding="utf-8") if log_path.exists() else "# Changelog\n"
        from datetime import datetime, timezone

        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entry = f"\n## {date}\n- generated {concepts_count} concepts\n"
        log_path.write_text(existing.rstrip() + entry + "\n", encoding="utf-8")

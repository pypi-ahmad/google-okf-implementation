"""Automated documentation generation from OKF metadata."""

from collections import Counter
from pathlib import Path

from okfhub.okf import OKFBundleLoader
from okfhub.utils.filesystem import ensure_dir


class DocumentationGenerator:
    """Generate project docs from an OKF bundle."""

    def generate(self, okf_root: Path, output_dir: Path) -> list[Path]:
        """Generate README, architecture summary, API docs, dependency report, and dataset catalog."""

        ensure_dir(output_dir)
        docs = OKFBundleLoader().load(okf_root)
        type_counts = Counter(doc.frontmatter.type for doc in docs)

        readme_path = output_dir / "README.generated.md"
        architecture_path = output_dir / "architecture.generated.md"
        api_path = output_dir / "api.generated.md"
        dependency_path = output_dir / "dependency_report.generated.md"
        catalog_path = output_dir / "dataset_catalog.generated.md"

        readme_path.write_text(self._render_readme(docs, type_counts), encoding="utf-8")
        architecture_path.write_text(self._render_architecture(type_counts), encoding="utf-8")
        api_path.write_text(self._render_api_docs(docs), encoding="utf-8")
        dependency_path.write_text(self._render_dependency_report(docs), encoding="utf-8")
        catalog_path.write_text(self._render_catalog(docs), encoding="utf-8")

        return [readme_path, architecture_path, api_path, dependency_path, catalog_path]

    def _render_readme(self, docs, counts: Counter) -> str:
        lines = ["# Enterprise OKF Knowledge Hub", "", "## Bundle Summary", ""]
        for concept_type, count in sorted(counts.items()):
            lines.append(f"- {concept_type}: {count}")
        lines.append("")
        lines.append("## Top Concepts")
        lines.append("")
        for doc in docs[:20]:
            lines.append(f"- {doc.frontmatter.title} (`{doc.frontmatter.type}`)")
        return "\n".join(lines) + "\n"

    def _render_architecture(self, counts: Counter) -> str:
        return (
            "# Architecture Overview\n\n"
            "Pipeline: Ingestion -> Extraction -> OKF -> Validation -> Graph -> Embeddings -> RAG Agent\n\n"
            "## Concept Distribution\n"
            + "\n".join(f"- {k}: {v}" for k, v in sorted(counts.items()))
            + "\n"
        )

    def _render_api_docs(self, docs) -> str:
        api_docs = [doc for doc in docs if doc.frontmatter.type == "api"]
        lines = ["# API Catalog", ""]
        if not api_docs:
            lines.append("No API concepts found.")
            return "\n".join(lines) + "\n"

        for doc in api_docs:
            lines.extend(
                [
                    f"## {doc.frontmatter.title}",
                    f"- Path: `{doc.relative_path}`",
                    f"- Description: {doc.frontmatter.description}",
                    f"- Resource: {doc.frontmatter.resource or 'n/a'}",
                    "",
                ]
            )

        return "\n".join(lines)

    def _render_catalog(self, docs) -> str:
        dataset_docs = [doc for doc in docs if doc.frontmatter.type in {"dataset", "table", "metric"}]
        lines = ["# Dataset Catalog", ""]

        for doc in dataset_docs:
            lines.append(
                f"- **{doc.frontmatter.title}** (`{doc.frontmatter.type}`): {doc.frontmatter.description}"
            )

        if len(lines) == 2:
            lines.append("No dataset-related concepts found.")

        return "\n".join(lines) + "\n"

    def _render_dependency_report(self, docs) -> str:
        lines = ["# Dependency Report", ""]
        dependency_counts = Counter()

        for doc in docs:
            dependency_counts[doc.frontmatter.type] += len(doc.links)

        lines.append("## Link Volume by Concept Type")
        lines.append("")
        for concept_type, count in sorted(dependency_counts.items()):
            lines.append(f"- {concept_type}: {count} outgoing links")

        lines.append("")
        lines.append("## Top Linked Concepts")
        lines.append("")

        linked = sorted(docs, key=lambda doc: len(doc.links), reverse=True)
        for doc in linked[:10]:
            lines.append(f"- {doc.frontmatter.title} (`{doc.frontmatter.type}`): {len(doc.links)} links")

        if len(linked) == 0:
            lines.append("No concepts found.")

        return "\n".join(lines) + "\n"

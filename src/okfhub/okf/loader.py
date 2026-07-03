"""Load existing OKF bundle markdown files into typed models."""

from pathlib import Path

import frontmatter

from okfhub.models import ConceptDocument, ConceptFrontmatter
from okfhub.utils.filesystem import list_markdown_files
from okfhub.utils.okf import concept_id_from_path
from okfhub.utils.text import extract_markdown_links

RESERVED_FILENAMES = {"index.md", "log.md"}


class OKFBundleLoader:
    """Read concept files from an OKF bundle."""

    def load(self, root: Path) -> list[ConceptDocument]:
        docs: list[ConceptDocument] = []

        for md_file in list_markdown_files(root):
            if md_file.name in RESERVED_FILENAMES:
                continue

            post = frontmatter.load(md_file)
            meta = post.metadata or {}
            front = ConceptFrontmatter(
                type=str(meta.get("type", "")),
                title=str(meta.get("title", "")),
                description=str(meta.get("description", "")),
                tags=[str(item) for item in meta.get("tags", [])] if isinstance(meta.get("tags"), list) else [],
                resource=str(meta.get("resource")) if meta.get("resource") is not None else None,
                timestamp=str(meta.get("timestamp", "")),
            )

            body = post.content
            docs.append(
                ConceptDocument(
                    concept_id=concept_id_from_path(root, md_file),
                    relative_path=md_file.relative_to(root).as_posix(),
                    frontmatter=front,
                    body=body,
                    links=extract_markdown_links(body),
                )
            )

        return docs

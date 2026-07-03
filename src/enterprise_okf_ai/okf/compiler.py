"""OKF compiler wrapper for concept-to-markdown generation."""

from __future__ import annotations

from pathlib import Path

from enterprise_okf_ai.okf.bundle_generator import BundleBuildReport, OKFBundleGenerator
from extractor.schema import EnterpriseConcepts
from generator.okf_writer import OKFWriter
from ingest.parser import ParsedDocument


class OKFCompiler:
    """Compile extracted enterprise concepts into strict OKF bundle files."""

    def __init__(self, target_dir: str | Path):
        self._writer = OKFWriter(target_dir)

    def compile(self, concepts: EnterpriseConcepts, source_text: str, resource: str) -> list[Path]:
        """Write concept artifacts to target OKF directory."""

        return self._writer.write(concepts=concepts, source_text=source_text, resource=resource)

    def build_bundle(self, documents: list[ParsedDocument], source_dir: str | Path) -> BundleBuildReport:
        """Build strict OKF bundle directly from normalized ingestion documents."""

        generator = OKFBundleGenerator(output_dir=self._writer.target_dir, source_dir=source_dir)
        return generator.build(documents)

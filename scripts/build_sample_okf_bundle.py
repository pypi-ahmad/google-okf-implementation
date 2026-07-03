"""Build a realistic sample OKF bundle from example enterprise documentation."""

from __future__ import annotations

import json
from pathlib import Path

from enterprise_okf_ai.ingestion import IngestionService
from enterprise_okf_ai.okf import OKFBundleGenerator
from ingest.parser import DocumentParser


def main() -> None:
    source_dir = Path("examples/enterprise_docs")
    output_dir = Path("examples/sample_okf_bundle")

    parser = DocumentParser(chunk_size_chars=1200, chunk_overlap_chars=150, recover_errors=True)
    ingestion = IngestionService(parser=parser)
    documents = ingestion.ingest(source_dir)

    report = OKFBundleGenerator(output_dir=output_dir, source_dir=source_dir).build(documents)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

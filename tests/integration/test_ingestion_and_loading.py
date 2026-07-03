from pathlib import Path

from okfhub.datasets import SyntheticEnterpriseCorpus
from okfhub.ingestion import IngestionService
from okfhub.settings import Settings


def test_synthetic_corpus_ingests_multiple_formats(tmp_path: Path) -> None:
    source_root = tmp_path / "raw"
    files = SyntheticEnterpriseCorpus(source_root).generate()

    assert len(files) >= 6

    service = IngestionService(Settings())
    chunks = service.ingest_directory(source_root)

    assert len(chunks) > 0
    suffixes = {chunk.source_path.suffix.lower() for chunk in chunks}
    assert ".md" in suffixes
    assert ".csv" in suffixes
    assert ".html" in suffixes

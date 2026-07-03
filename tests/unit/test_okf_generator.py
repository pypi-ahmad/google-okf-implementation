from pathlib import Path

import frontmatter

from okfhub.models import ExtractedConcept
from okfhub.okf import OKFBundleGenerator


def test_okf_bundle_generator_creates_expected_files(tmp_path: Path) -> None:
    root = tmp_path / "okf"
    concepts = [
        ExtractedConcept(
            concept_id="api_orders",
            concept_type="api",
            title="Orders API",
            description="Updates order status",
            tags=["orders", "api"],
            resource="docs/orders_api.md",
            dependencies=[],
        ),
        ExtractedConcept(
            concept_id="dataset_orders",
            concept_type="dataset",
            title="Orders Dataset",
            description="Warehouse orders table",
            tags=["warehouse"],
            resource="warehouse/orders",
            dependencies=["api_orders"],
        ),
    ]

    generated = OKFBundleGenerator(root).generate(concepts)

    assert len(generated) == 2
    assert (root / "apis").exists()
    assert (root / "datasets").exists()
    assert (root / "index.md").exists()
    assert (root / "log.md").exists()

    api_file = root / "apis" / "orders-api.md"
    post = frontmatter.load(api_file)
    assert post.metadata["type"] == "api"
    assert post.metadata["title"] == "Orders API"
    assert "# Citations" in post.content

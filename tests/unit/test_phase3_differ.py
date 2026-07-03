from pathlib import Path

from generator.differ import OKFDiffer


def _write_doc(path: Path, frontmatter: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8")


def test_okf_differ_reports_metrics_renamed_apis_and_schema_updates(tmp_path: Path) -> None:
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"

    _write_doc(
        v1 / "apis" / "orders-api.md",
        """
type: api
title: Orders API
description: Legacy endpoint
tags: [api]
resource: /v1/orders
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "Legacy body",
    )
    _write_doc(
        v1 / "metrics" / "mau.md",
        """
type: metric
title: MAU
description: v1 def
tags: [metric]
resource: metrics.mau
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "Old formula",
    )
    _write_doc(
        v1 / "datasets" / "orders.md",
        """
type: dataset
title: Orders
description: Dataset schema v1
tags: [dataset]
resource: warehouse.orders
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "Columns: order_id",
    )

    _write_doc(
        v2 / "apis" / "orders-service-api.md",
        """
type: api
title: Orders Service API
description: New endpoint
tags: [api]
resource: /v1/orders
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "Updated body",
    )
    _write_doc(
        v2 / "metrics" / "mau.md",
        """
type: metric
title: MAU
description: v2 def
tags: [metric]
resource: metrics.mau
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "New formula",
    )
    _write_doc(
        v2 / "datasets" / "orders.md",
        """
type: dataset
title: Orders
description: Dataset schema v2
tags: [dataset]
resource: warehouse.orders
timestamp: 2026-07-03T00:00:00Z
""".strip(),
        "Columns: order_id, customer_id",
    )

    differ = OKFDiffer()
    summary = differ.compare(v1, v2)

    assert summary.changed_metrics == ["metrics/mau.md"]
    assert summary.updated_schemas == ["datasets/orders.md"]
    assert summary.renamed_apis

    markdown = differ.to_markdown(summary, v1_label="v1", v2_label="v2")
    assert "Changed Metrics" in markdown
    assert "Renamed APIs" in markdown

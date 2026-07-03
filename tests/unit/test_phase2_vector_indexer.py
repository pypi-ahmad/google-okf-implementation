from pathlib import Path

from vector_db.indexer import OKFVectorIndexer


def _write_concept(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """
---
type: api
title: Orders API
description: Updates orders
tags: [api,orders]
resource: orders.api
timestamp: 2026-07-03T00:00:00Z
---

""".strip()
        + "\n\n"
        + body
        + "\n",
        encoding="utf-8",
    )


def test_vector_indexer_is_idempotent(tmp_path: Path) -> None:
    okf_root = tmp_path / "okf"
    persist_dir = tmp_path / "vector"
    file_path = okf_root / "apis" / "orders-api.md"

    _write_concept(file_path, "First version of API documentation.")

    def _fake_embed(texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), 1.0, 0.0] for text in texts]

    indexer = OKFVectorIndexer(
        okf_dir=okf_root,
        persist_dir=persist_dir,
        embedding_fn=_fake_embed,
    )

    first = indexer.index()
    second = indexer.index()

    assert first["files_changed"] == 1
    assert first["chunks_indexed"] >= 1
    assert second["files_changed"] == 0
    assert second["chunks_indexed"] == 0

    _write_concept(file_path, "Second version of API documentation with updates.")
    third = indexer.index()

    assert third["files_changed"] == 1
    assert third["chunks_indexed"] >= 1

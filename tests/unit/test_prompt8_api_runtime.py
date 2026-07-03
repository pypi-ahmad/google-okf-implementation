from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from enterprise_okf_ai.api.app import create_app
from enterprise_okf_ai.core.embeddings import deterministic_embedding
from enterprise_okf_ai.core.settings import Settings
from enterprise_okf_ai.ingestion import IngestionService
from enterprise_okf_ai.okf import OKFBundleGenerator
from ingest.parser import DocumentParser
from vector_db.indexer import OKFVectorIndexer


def _build_runtime_assets(tmp_path: Path) -> tuple[Path, Path]:
    raw_dir = tmp_path / "raw_docs"
    okf_dir = tmp_path / "okf_bundle"
    vector_dir = tmp_path / "vector_store"

    (raw_dir / "apis").mkdir(parents=True, exist_ok=True)
    (raw_dir / "datasets").mkdir(parents=True, exist_ok=True)
    (raw_dir / "metrics").mkdir(parents=True, exist_ok=True)

    (raw_dir / "apis" / "orders_api.md").write_text(
        "# Orders API\nPATCH /v2/orders/{order_id} updates order status.\nDependencies:\n- Orders Dataset\n",
        encoding="utf-8",
    )
    (raw_dir / "datasets" / "orders_dataset.md").write_text(
        "# Orders Dataset\nCanonical order records.\n",
        encoding="utf-8",
    )
    (raw_dir / "metrics" / "mau.md").write_text(
        "# Monthly Active Users\nCOUNT(DISTINCT customer_id).\n",
        encoding="utf-8",
    )

    parsed = IngestionService(parser=DocumentParser()).ingest(raw_dir, recursive=True, fail_fast=True)
    OKFBundleGenerator(output_dir=okf_dir, source_dir=raw_dir).build(parsed)
    OKFVectorIndexer(okf_dir=okf_dir, persist_dir=vector_dir, embedding_fn=deterministic_embedding).index()
    return okf_dir, vector_dir


@pytest.mark.asyncio
async def test_prompt8_fastapi_runtime_agent_and_retrieval_endpoints(tmp_path: Path) -> None:
    okf_dir, vector_dir = _build_runtime_assets(tmp_path)
    benchmark_path = tmp_path / "agent_benchmark.json"
    benchmark_path.write_text(
        json.dumps(
            [
                {
                    "case_id": "case-1",
                    "question": "Which API updates order status?",
                    "expected_concepts": ["apis/orders-api"],
                    "support_terms": ["PATCH /v2/orders/{order_id}"],
                    "should_abstain": False,
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )

    settings = Settings(
        okf_dir=okf_dir,
        vector_dir=vector_dir,
        graph_dir=tmp_path / "graph",
    )
    app = create_app(settings=settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        retrieval_response = await client.post(
            "/retrieval/search",
            json={
                "query": "Which API updates order status?",
                "top_k": 5,
                "route": "auto",
                "with_trace": True,
            },
        )
        assert retrieval_response.status_code == 200
        retrieval_payload = retrieval_response.json()
        assert retrieval_payload["results"]
        assert retrieval_payload["router_trace"]

        ask_response = await client.post(
            "/agent/ask",
            json={
                "question": "Which API updates order status and what evidence supports this?",
                "top_k": 6,
            },
        )
        assert ask_response.status_code == 200
        ask_payload = ask_response.json()
        assert "answer" in ask_payload
        assert "tool_calls" in ask_payload
        assert "supported" in ask_payload

        eval_response = await client.post(
            "/agent/evaluate",
            json={
                "benchmark_path": benchmark_path.as_posix(),
                "top_k": 6,
            },
        )
        assert eval_response.status_code == 200
        eval_payload = eval_response.json()
        assert "summary" in eval_payload
        assert "items" in eval_payload
        assert eval_payload["summary"]["total_cases"] == 1

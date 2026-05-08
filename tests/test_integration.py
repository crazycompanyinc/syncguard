from __future__ import annotations

import asyncio

from click.testing import CliRunner
from httpx import ASGITransport, AsyncClient

from syncguard.cli import main
from syncguard.detector.detector import DriftDetector
from syncguard.extractor.extractor import InvariantExtractor
from syncguard.ledger.ledger import DriftLedger
from syncguard.server.app import create_app


def test_full_pipeline(sample_project) -> None:
    invariants = InvariantExtractor().extract(sample_project)
    diff = (
        "diff --git a/api/models.py b/api/models.py\n--- a/api/models.py\n+++ b/api/models.py\n@@ -1 +1 @@\n-    user_id: str\n+    user_id: int\n"
        "diff --git a/api/handlers.py b/api/handlers.py\n--- a/api/handlers.py\n+++ b/api/handlers.py\n@@ -1 +1 @@\n-    return {'data': {}, 'meta': {}, 'links': {}}\n+    return {'result': {}}\n"
    )
    incidents = DriftDetector(invariants, sample_project).check_diff(diff)
    debt = DriftLedger().build_debt(incidents)
    assert len(incidents) >= 2
    assert debt


def test_api_health_and_extract(sample_project) -> None:
    async def run() -> None:
        async with AsyncClient(transport=ASGITransport(app=create_app(sample_project)), base_url="http://test") as client:
            assert (await client.get("/health")).json() == {"status": "ok"}
            response = await client.post("/extract", json={"path": str(sample_project)})
            assert response.status_code == 200
            assert response.json()["count"] >= 3

    asyncio.run(run())


def test_cli_demo_runs() -> None:
    result = CliRunner().invoke(main, ["demo"])
    assert result.exit_code == 0, result.output
    assert "Detected drift" in result.output
    assert "Predictions" in result.output

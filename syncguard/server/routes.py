"""FastAPI route registration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from syncguard.core.db import SyncGuardDB
from syncguard.detector.detector import DriftDetector
from syncguard.extractor.extractor import InvariantExtractor
from syncguard.ledger.ledger import DriftLedger


class ExtractRequest(BaseModel):
    path: str = "."


class CheckRequest(BaseModel):
    diff: str
    path: str = "."


def build_router(root: str | Path = ".") -> APIRouter:
    router = APIRouter()
    db = SyncGuardDB(root)

    @router.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @router.post("/extract")
    async def extract(req: ExtractRequest) -> dict[str, Any]:
        invariants = InvariantExtractor().extract(req.path)
        db.clear_invariants()
        db.save_invariants(invariants)
        return {"count": len(invariants), "invariants": [inv.to_dict() for inv in invariants]}

    @router.get("/invariants")
    async def invariants() -> list[dict[str, Any]]:
        return [inv.to_dict() for inv in db.list_invariants()]

    @router.post("/check")
    async def check(req: CheckRequest) -> dict[str, Any]:
        detector = DriftDetector(db.list_invariants(), root=req.path)
        incidents = detector.check_diff(req.diff)
        db.save_drifts(incidents)
        debt = DriftLedger().build_debt(db.list_drifts())
        db.save_debt(debt)
        return {"count": len(incidents), "drifts": [incident.to_dict() for incident in incidents]}

    @router.get("/drifts")
    async def drifts() -> list[dict[str, Any]]:
        return [drift.to_dict() for drift in db.list_drifts()]

    @router.get("/debt")
    async def debt() -> list[dict[str, Any]]:
        return [entry.to_dict() for entry in db.list_debt()]

    @router.get("/predict")
    async def predict() -> dict[str, list[str]]:
        entries = db.list_debt()
        return {"predictions": DriftLedger().predictions(entries)}

    return router

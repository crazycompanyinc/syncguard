"""Dataclass models used across SyncGuard."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

InvariantType = Literal[
    "data_shape",
    "cross_module",
    "convention",
    "behavioral",
    "type_contract",
    "schema_evolution",
    "api_contract",
    "database_schema",
    "configuration",
    "test_inferred",
]
Severity = Literal["low", "medium", "high", "critical"]
DriftType = Literal["new_violation", "worsening", "accumulated"]
DriftStatus = Literal["open", "acknowledged", "resolved", "ignored"]
DebtTrend = Literal["improving", "stable", "worsening"]


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Invariant:
    """An implicit rule extracted from source code."""

    name: str
    description: str
    invariant_type: InvariantType
    scope: str
    source_files: list[str]
    confidence: float
    evidence: dict[str, Any]
    id: str = field(default_factory=lambda: f"inv_{uuid4().hex[:12]}")
    created_at: str = field(default_factory=utcnow)
    last_verified: str = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Invariant":
        return cls(**data)


@dataclass(slots=True)
class DriftIncident:
    """A detected violation of an invariant."""

    invariant_id: str
    file_path: str
    diff_excerpt: str
    severity: Severity
    drift_type: DriftType
    status: DriftStatus
    impact_score: float
    affected_files: list[str]
    suggested_fix: str
    id: str = field(default_factory=lambda: f"drift_{uuid4().hex[:12]}")
    detected_at: str = field(default_factory=utcnow)
    resolved_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DriftIncident":
        return cls(**data)


@dataclass(slots=True)
class DriftDebtEntry:
    """Accumulated drift debt for a module or file."""

    file_path: str
    total_drifts_detected: int
    total_drifts_resolved: int
    net_debt: int
    debt_trend: DebtTrend
    last_incident_at: str | None
    estimated_break_prediction: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DriftDebtEntry":
        return cls(**data)

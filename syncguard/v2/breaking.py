"""Pre-merge breaking change detection."""

from __future__ import annotations

from dataclasses import dataclass

from syncguard.v2.api_contracts import APIContract, APIContractMonitor
from syncguard.v2.schema import SchemaEvolutionTracker, SchemaVersion


@dataclass(slots=True)
class BreakingChange:
    surface: str
    consumer: str
    reason: str


class BreakingChangeDetector:
    """Detect whether proposed changes break known consumers."""

    def __init__(self) -> None:
        self.schemas = SchemaEvolutionTracker()
        self.apis = APIContractMonitor()

    def schema_breaks(self, old: SchemaVersion, new: SchemaVersion, consumers: dict[str, set[str]]) -> list[BreakingChange]:
        changes = self.schemas.compare(old, new)
        breakages = self.schemas.downstream_breakages(changes, consumers)
        return [BreakingChange(old.name, consumer, f"changed fields: {', '.join(fields)}") for consumer, fields in sorted(breakages.items())]

    def api_breaks(self, old: APIContract, new: APIContract, consumers: list[str]) -> list[BreakingChange]:
        drifts = self.apis.compare(old, new)
        breaking = [drift for drift in drifts if drift.breaking]
        return [BreakingChange(old.key, consumer, ", ".join(drift.message for drift in breaking)) for consumer in consumers] if breaking else []

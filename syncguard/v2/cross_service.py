"""Cross-service invariant detection."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

from syncguard.core.models import Invariant


@dataclass(slots=True)
class ServiceFieldContract:
    service: str
    field: str
    field_type: str
    direction: str
    source_file: str


class CrossServiceInvariantDetector:
    """Find producer/consumer contract mismatches across microservices."""

    def detect(self, contracts: list[ServiceFieldContract]) -> list[Invariant]:
        by_field: dict[str, list[ServiceFieldContract]] = defaultdict(list)
        for contract in contracts:
            by_field[contract.field].append(contract)
        invariants: list[Invariant] = []
        for field, items in sorted(by_field.items()):
            types = {item.field_type for item in items}
            if len(items) < 2:
                continue
            producers = [item for item in items if item.direction == "produces"]
            consumers = [item for item in items if item.direction == "consumes"]
            if producers and consumers and len(types) > 1:
                expected = producers[0].field_type
                invariants.append(
                    Invariant(
                        name=f"{field} cross-service contract drift",
                        description=f"Services disagree on `{field}` type.",
                        invariant_type="cross_module",
                        scope=field,
                        source_files=sorted({item.source_file for item in items}),
                        confidence=1.0,
                        evidence={
                            "field": field,
                            "expected_type": expected,
                            "participants": [asdict(item) for item in items],
                            "mismatches": [asdict(item) for item in items if item.field_type != expected],
                        },
                    )
                )
        return invariants

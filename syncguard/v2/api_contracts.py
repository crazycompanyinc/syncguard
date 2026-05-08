"""REST/gRPC API contract monitoring."""

from __future__ import annotations

from dataclasses import dataclass

from syncguard.v2.schema import SchemaChange, SchemaEvolutionTracker, SchemaVersion


@dataclass(slots=True)
class APIContract:
    service: str
    endpoint: str
    method: str
    version: str
    response: SchemaVersion
    error: SchemaVersion
    auth_required: bool

    @property
    def key(self) -> str:
        return f"{self.service}:{self.method.upper()} {self.endpoint}"


@dataclass(slots=True)
class APIContractDrift:
    contract_key: str
    area: str
    breaking: bool
    message: str
    changes: list[SchemaChange]


class APIContractMonitor:
    """Detect silent changes in response shape, error shape, or auth policy."""

    def __init__(self) -> None:
        self.schemas = SchemaEvolutionTracker()

    def compare(self, old: APIContract, new: APIContract) -> list[APIContractDrift]:
        drifts: list[APIContractDrift] = []
        response_changes = self.schemas.compare(old.response, new.response)
        if response_changes:
            drifts.append(APIContractDrift(old.key, "response", any(change.breaking for change in response_changes), "response shape changed", response_changes))
        error_changes = self.schemas.compare(old.error, new.error)
        if error_changes:
            drifts.append(APIContractDrift(old.key, "error", any(change.breaking for change in error_changes), "error format changed", error_changes))
        if old.auth_required != new.auth_required:
            message = "authentication requirement changed"
            drifts.append(APIContractDrift(old.key, "auth", True, message, []))
        return drifts

"""Drift debt quantification."""

from __future__ import annotations

from dataclasses import dataclass

from syncguard.core.models import DriftIncident


@dataclass(slots=True)
class DebtEstimate:
    drift_id: str
    hours: float
    dollars: float
    rationale: str


class DebtQuantifier:
    """Assign time and dollar estimates to unresolved drift."""

    def __init__(self, hourly_rate: float = 150.0) -> None:
        self.hourly_rate = hourly_rate

    def estimate(self, incident: DriftIncident) -> DebtEstimate:
        affected = max(1, len(incident.affected_files))
        severity_multiplier = {"low": 1.0, "medium": 2.0, "high": 4.0, "critical": 8.0}[incident.severity]
        hours = round((1.0 + affected * 0.75) * severity_multiplier * max(0.5, incident.impact_score), 1)
        return DebtEstimate(
            drift_id=incident.id,
            hours=hours,
            dollars=round(hours * self.hourly_rate, 2),
            rationale=f"{incident.severity} drift affecting {affected} file(s) at impact {incident.impact_score:.2f}",
        )

    def total(self, incidents: list[DriftIncident]) -> DebtEstimate:
        estimates = [self.estimate(incident) for incident in incidents if incident.status != "resolved"]
        hours = round(sum(item.hours for item in estimates), 1)
        return DebtEstimate("total", hours, round(hours * self.hourly_rate, 2), f"{len(estimates)} unresolved drift incident(s)")

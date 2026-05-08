"""Team-oriented drift reports."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from syncguard.core.models import DriftIncident
from syncguard.v2.debt import DebtQuantifier


@dataclass(slots=True)
class TeamDriftReport:
    team: str
    incidents: int
    estimated_hours: float
    estimated_dollars: float
    files: list[str]


class TeamDriftReporter:
    """Aggregate drift debt by ownership map."""

    def __init__(self, quantifier: DebtQuantifier | None = None) -> None:
        self.quantifier = quantifier or DebtQuantifier()

    def build(self, incidents: list[DriftIncident], ownership: dict[str, str]) -> list[TeamDriftReport]:
        grouped: dict[str, list[DriftIncident]] = defaultdict(list)
        for incident in incidents:
            grouped[_team_for(incident.file_path, ownership)].append(incident)
        reports: list[TeamDriftReport] = []
        for team, items in sorted(grouped.items()):
            estimate = self.quantifier.total(items)
            reports.append(TeamDriftReport(team, len(items), estimate.hours, estimate.dollars, sorted({item.file_path for item in items})))
        return reports


def _team_for(file_path: str, ownership: dict[str, str]) -> str:
    matches = [(prefix, team) for prefix, team in ownership.items() if file_path.startswith(prefix)]
    if not matches:
        return "unowned"
    return max(matches, key=lambda item: len(item[0]))[1]

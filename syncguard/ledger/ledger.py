"""Historical drift tracking and prediction."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from syncguard.core.models import DriftDebtEntry, DriftIncident


class DriftLedger:
    """Build debt reports and simple deterministic break predictions."""

    def build_debt(self, incidents: list[DriftIncident]) -> list[DriftDebtEntry]:
        by_file: dict[str, list[DriftIncident]] = defaultdict(list)
        for incident in incidents:
            by_file[incident.file_path].append(incident)
            for affected in incident.affected_files:
                by_file[affected].append(incident)
        entries: list[DriftDebtEntry] = []
        for file_path, items in sorted(by_file.items()):
            detected = len(items)
            resolved = sum(1 for item in items if item.status == "resolved")
            net = detected - resolved
            trend = "stable"
            if net >= 3 or any(item.impact_score >= 0.75 for item in items):
                trend = "worsening"
            elif resolved and net == 0:
                trend = "improving"
            prediction = self._prediction(file_path, net, items)
            entries.append(
                DriftDebtEntry(
                    file_path=file_path,
                    total_drifts_detected=detected,
                    total_drifts_resolved=resolved,
                    net_debt=net,
                    debt_trend=trend,  # type: ignore[arg-type]
                    last_incident_at=max((item.detected_at for item in items), default=None),
                    estimated_break_prediction=prediction,
                )
            )
        return entries

    def predictions(self, entries: list[DriftDebtEntry]) -> list[str]:
        predictions = []
        for entry in entries:
            if entry.net_debt > 0:
                predictions.append(entry.estimated_break_prediction)
        return predictions

    def _prediction(self, file_path: str, net: int, incidents: list[DriftIncident]) -> str:
        if net <= 0:
            return f"{file_path} has no current drift break prediction."
        highest = max((incident.impact_score for incident in incidents), default=0.0)
        changes = max(1, 5 - net - int(highest))
        label = _prediction_label(file_path)
        return f"If drift continues at this rate, {label} will likely break within {changes} changes."


def _prediction_label(file_path: str) -> str:
    path = Path(file_path)
    if len(path.parts) >= 2 and path.parts[-2] == "services":
        return f"{path.stem}-service"
    return file_path.replace("/", "-").replace(".py", "")

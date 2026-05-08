from __future__ import annotations

from syncguard.core.models import DriftIncident
from syncguard.ledger.ledger import DriftLedger


def test_ledger_builds_debt_and_predictions() -> None:
    incident = DriftIncident("inv", "a.py", "+x", "high", "new_violation", "open", 0.8, ["b.py"], "fix")
    entries = DriftLedger().build_debt([incident])
    assert {entry.file_path for entry in entries} == {"a.py", "b.py"}
    assert DriftLedger().predictions(entries)


def test_resolved_debt_improves() -> None:
    incident = DriftIncident("inv", "a.py", "+x", "low", "new_violation", "resolved", 0.2, [], "fix")
    entries = DriftLedger().build_debt([incident])
    assert entries[0].debt_trend == "improving"

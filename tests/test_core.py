from __future__ import annotations

from syncguard.core.db import SyncGuardDB
from syncguard.core.models import DriftDebtEntry, DriftIncident, Invariant


def test_model_roundtrip() -> None:
    inv = Invariant("name", "desc", "data_shape", "api", ["api.py"], 1.0, {"shape": ["data"]})
    assert Invariant.from_dict(inv.to_dict()).id == inv.id
    drift = DriftIncident(inv.id, "api.py", "+x", "low", "new_violation", "open", 0.3, [], "fix")
    assert DriftIncident.from_dict(drift.to_dict()).id == drift.id
    debt = DriftDebtEntry("api.py", 1, 0, 1, "stable", None, "soon")
    assert DriftDebtEntry.from_dict(debt.to_dict()).file_path == "api.py"


def test_db_persists_records(tmp_path) -> None:
    db = SyncGuardDB(tmp_path)
    inv = Invariant("name", "desc", "data_shape", "api", ["api.py"], 1.0, {})
    drift = DriftIncident(inv.id, "api.py", "+x", "medium", "new_violation", "open", 0.5, [], "fix")
    debt = DriftDebtEntry("api.py", 1, 0, 1, "stable", drift.detected_at, "prediction")
    db.save_invariants([inv])
    db.save_drifts([drift])
    db.save_debt([debt])
    assert db.list_invariants()[0].id == inv.id
    assert db.get_drift(drift.id).id == drift.id  # type: ignore[union-attr]
    assert db.list_debt("api.py")[0].net_debt == 1


def test_db_filters_invariants_by_type(tmp_path) -> None:
    db = SyncGuardDB(tmp_path)
    data = Invariant("data", "desc", "data_shape", "api", ["api.py"], 1.0, {})
    behavior = Invariant("behavior", "desc", "behavioral", "migrations", ["m.py"], 1.0, {})
    db.save_invariants([data, behavior])
    assert [inv.id for inv in db.list_invariants("behavioral")] == [behavior.id]


def test_clear_invariants(tmp_path) -> None:
    db = SyncGuardDB(tmp_path)
    db.save_invariants([Invariant("name", "desc", "data_shape", "api", ["api.py"], 1.0, {})])
    db.clear_invariants()
    assert db.list_invariants() == []

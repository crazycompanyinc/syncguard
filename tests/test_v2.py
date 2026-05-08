from __future__ import annotations

from pathlib import Path

from syncguard.core.models import DriftIncident, Invariant
from syncguard.v2 import (
    APIContractMonitor,
    AutoFixGenerator,
    BreakingChangeDetector,
    ConfigurationDriftTracker,
    CrossServiceInvariantDetector,
    DatabaseSchemaDriftMonitor,
    DebtQuantifier,
    InvariantGraphVisualizer,
    SchemaEvolutionTracker,
    SemVerEnforcer,
    TeamDriftReporter,
    TestInvariantMiner,
)
from syncguard.v2.api_contracts import APIContract
from syncguard.v2.cross_service import ServiceFieldContract


def test_schema_evolution_detects_downstream_breakage() -> None:
    tracker = SchemaEvolutionTracker()
    old = tracker.infer_from_sample("User", "1.0.0", {"id": "u1", "email": "a@example.com"})
    new = tracker.infer_from_sample("User", "2.0.0", {"id": 1})
    changes = tracker.compare(old, new)
    breakages = tracker.downstream_breakages(changes, {"billing": {"id"}, "marketing": {"email"}})
    assert {change.change_type for change in changes} == {"type_changed", "removed_field"}
    assert breakages == {"billing": ["id"], "marketing": ["email"]}


def test_api_contract_monitor_tracks_response_error_and_auth() -> None:
    tracker = SchemaEvolutionTracker()
    old = APIContract(
        "users",
        "/users/{id}",
        "GET",
        "1.0.0",
        tracker.infer_from_sample("UserResponse", "1.0.0", {"id": "u1"}),
        tracker.infer_from_sample("Error", "1.0.0", {"error": "missing"}),
        True,
    )
    new = APIContract(
        "users",
        "/users/{id}",
        "GET",
        "1.1.0",
        tracker.infer_from_sample("UserResponse", "1.1.0", {"id": 1}),
        tracker.infer_from_sample("Error", "1.1.0", {"message": "missing"}),
        False,
    )
    drifts = APIContractMonitor().compare(old, new)
    assert {drift.area for drift in drifts} == {"response", "error", "auth"}
    assert all(drift.breaking for drift in drifts)


def test_cross_service_invariants_find_type_mismatch() -> None:
    detector = CrossServiceInvariantDetector()
    invariants = detector.detect(
        [
            ServiceFieldContract("accounts", "user_id", "UUID", "produces", "accounts/events.py"),
            ServiceFieldContract("billing", "user_id", "int", "consumes", "billing/consumer.py"),
        ]
    )
    assert len(invariants) == 1
    assert invariants[0].evidence["mismatches"][0]["service"] == "billing"


def test_database_schema_drift_breaks_app_assumptions() -> None:
    monitor = DatabaseSchemaDriftMonitor()
    old = monitor.parse_create_table("CREATE TABLE users (id uuid, email text, name text)")
    new = monitor.parse_create_table("CREATE TABLE users (id integer, name text)")
    drifts = monitor.compare(old, new, {"users": {"id", "email"}})
    assert [(drift.column, drift.breaking) for drift in drifts] == [("email", True), ("id", True)]


def test_configuration_drift_tracks_environment_differences() -> None:
    drifts = ConfigurationDriftTracker().compare(
        {"staging": {"feature_flag": False}, "production": {"feature_flag": True}},
        {"feature_flag"},
    )
    assert drifts[0].key == "feature_flag"
    assert drifts[0].severity == "high"


def test_semver_and_breaking_change_detection() -> None:
    tracker = SchemaEvolutionTracker()
    old = tracker.infer_from_sample("User", "1.0.0", {"id": "u1"})
    new = tracker.infer_from_sample("User", "1.1.0", {"id": 1})
    changes = tracker.compare(old, new)
    decision = SemVerEnforcer().validate("1.0.0", "1.1.0", changes)
    breaks = BreakingChangeDetector().schema_breaks(old, new, {"billing": {"id"}})
    assert decision.required_bump == "major"
    assert not decision.valid
    assert breaks[0].consumer == "billing"


def test_test_invariant_miner(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_contract.py").write_text(
        "def test_response():\n"
        "    response = {'data': {}, 'meta': {}}\n"
        "    assert 'data' in response\n"
        "    assert response['meta'] == {}\n",
        encoding="utf-8",
    )
    invariants = TestInvariantMiner().mine(tmp_path)
    assert {invariant.scope for invariant in invariants} == {"data", "meta"}


def test_debt_team_report_visualization_and_autofix() -> None:
    invariant = Invariant(
        name="user_id is str",
        description="user_id contract",
        invariant_type="type_contract",
        scope="user_id",
        source_files=["api/models.py"],
        confidence=1.0,
        evidence={"field": "user_id", "expected_type": "str"},
    )
    incident = DriftIncident(
        invariant_id=invariant.id,
        file_path="api/models.py",
        diff_excerpt="+ user_id: int",
        severity="high",
        drift_type="new_violation",
        status="open",
        impact_score=0.8,
        affected_files=["services/billing.py"],
        suggested_fix="fix it",
    )
    estimate = DebtQuantifier(hourly_rate=100).estimate(incident)
    report = TeamDriftReporter(DebtQuantifier(hourly_rate=100)).build([incident], {"api/": "Team Alpha"})
    dot = InvariantGraphVisualizer().to_dot([invariant], [incident])
    fix = AutoFixGenerator().generate(invariant, incident, "class User:\n    user_id: int\n")
    assert estimate.dollars > 0
    assert report[0].team == "Team Alpha"
    assert 'color="red"' in dot
    assert fix is not None
    assert "user_id: str" in fix.patched

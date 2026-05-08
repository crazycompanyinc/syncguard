"""Click command line interface for SyncGuard."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Iterable

import click
import uvicorn

from syncguard.core.db import SyncGuardDB
from syncguard.core.models import DriftIncident, Invariant
from syncguard.detector.detector import DriftDetector
from syncguard.extractor.extractor import InvariantExtractor
from syncguard.ledger.ledger import DriftLedger
from syncguard.server.app import create_app
from syncguard.v2 import (
    APIContractMonitor,
    ConfigurationDriftTracker,
    DebtQuantifier,
    InvariantGraphVisualizer,
    SchemaEvolutionTracker,
    SemVerEnforcer,
    TeamDriftReporter,
    TestInvariantMiner,
)
from syncguard.v2.api_contracts import APIContract


@click.group()
def main() -> None:
    """Detect implicit invariant drift before it becomes production debt."""


@main.command()
def init() -> None:
    """Initialize SyncGuard in the current directory."""
    db = SyncGuardDB(".")
    click.echo(f"Initialized SyncGuard at {db.db_path}")


@main.command()
@click.option("--path", "scan_path", default=".", help="Path to scan.")
def extract(scan_path: str) -> None:
    """Scan a codebase and extract invariants."""
    invariants = InvariantExtractor().extract(scan_path)
    db = SyncGuardDB(".")
    db.clear_invariants()
    db.save_invariants(invariants)
    click.echo(f"Extracted {len(invariants)} invariants")
    _print_invariants(invariants)


@main.command()
@click.option("--diff", "diff_file", type=click.Path(exists=True), help="Diff file to check.")
@click.option("--staged", is_flag=True, help="Check staged git changes.")
def check(diff_file: str | None, staged: bool) -> None:
    """Check current changes against extracted invariants."""
    db = SyncGuardDB(".")
    invariants = db.list_invariants()
    if not invariants:
        invariants = InvariantExtractor().extract(".")
        db.save_invariants(invariants)
    detector = DriftDetector(invariants, ".")
    if diff_file:
        incidents = detector.check_diff_file(diff_file)
    else:
        incidents = detector.check_git(staged=staged)
    _record_and_print_drifts(db, incidents)


@main.command()
@click.option("--file", "file_path", help="Only show debt for this file.")
def debt(file_path: str | None) -> None:
    """Show drift debt report."""
    db = SyncGuardDB(".")
    entries = db.list_debt(file_path)
    if not entries:
        entries = DriftLedger().build_debt(db.list_drifts())
        db.save_debt(entries)
    for entry in entries:
        click.echo(
            f"{entry.file_path}: net={entry.net_debt} detected={entry.total_drifts_detected} "
            f"resolved={entry.total_drifts_resolved} trend={entry.debt_trend}"
        )
        click.echo(f"  {entry.estimated_break_prediction}")


@main.command(name="patterns")
@click.option("--type", "invariant_type", help="Filter by invariant type.")
def patterns_cmd(invariant_type: str | None) -> None:
    """Show extracted invariants."""
    _print_invariants(SyncGuardDB(".").list_invariants(invariant_type))


@main.command()
@click.option("--id", "drift_id", required=True, help="Drift incident id.")
def fix(drift_id: str) -> None:
    """Show suggested fix for a drift."""
    drift = SyncGuardDB(".").get_drift(drift_id)
    if not drift:
        raise click.ClickException(f"Unknown drift id: {drift_id}")
    click.echo(drift.suggested_fix)


@main.command()
def ledger() -> None:
    """Show drift ledger/history."""
    drifts = SyncGuardDB(".").list_drifts()
    if not drifts:
        click.echo("No drift incidents recorded")
        return
    _print_drifts(drifts)


@main.command()
def predict() -> None:
    """Predict where drift will cause breaks."""
    db = SyncGuardDB(".")
    entries = db.list_debt() or DriftLedger().build_debt(db.list_drifts())
    for line in DriftLedger().predictions(entries):
        click.echo(line)


@main.command(name="team-report")
def team_report() -> None:
    """Show drift debt grouped by team ownership."""
    db = SyncGuardDB(".")
    ownership = {"api/": "Team Alpha", "services/": "Team Beta", "migrations/": "Platform"}
    reports = TeamDriftReporter().build(db.list_drifts(), ownership)
    for report in reports:
        click.echo(f"{report.team}: incidents={report.incidents} hours={report.estimated_hours:.1f} dollars=${report.estimated_dollars:.2f}")


@main.command(name="graph")
def graph() -> None:
    """Print the invariant graph as Graphviz DOT."""
    db = SyncGuardDB(".")
    click.echo(InvariantGraphVisualizer().to_dot(db.list_invariants(), db.list_drifts()))


@main.command()
@click.option("--port", default=8000, show_default=True, help="Port for the API server.")
def serve(port: int) -> None:
    """Start the SyncGuard API server."""
    uvicorn.run(create_app("."), host="127.0.0.1", port=port)


@main.command()
def demo() -> None:
    """Run a built-in demo scenario."""
    with tempfile.TemporaryDirectory(prefix="syncguard-demo-") as temp:
        root = Path(temp)
        _create_demo_project(root)
        subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        extractor = InvariantExtractor()
        invariants = extractor.extract(root)
        click.echo(f"Demo project: {root}")
        click.echo(f"Extracted {len(invariants)} invariants")
        _print_invariants(invariants)

        _introduce_demo_drift(root)
        diff = subprocess.check_output(["git", "diff"], cwd=root, text=True)
        incidents = DriftDetector(invariants, root).check_diff(diff)
        click.echo("")
        click.echo("Detected drift")
        _print_drifts(incidents)

        debt_entries = DriftLedger().build_debt(incidents)
        click.echo("")
        click.echo("Debt report")
        for entry in debt_entries:
            click.echo(f"{entry.file_path}: net={entry.net_debt} trend={entry.debt_trend}")

        click.echo("")
        click.echo("Predictions")
        for line in DriftLedger().predictions(debt_entries):
            click.echo(line)

        click.echo("")
        click.echo("v2 contract monitoring")
        schemas = SchemaEvolutionTracker()
        old_user = schemas.infer_from_sample("UserResponse", "1.2.0", {"id": "u1", "email": "a@example.com"})
        new_user = schemas.infer_from_sample("UserResponse", "1.3.0", {"id": 1, "email": "a@example.com", "plan": "pro"})
        schema_changes = schemas.compare(old_user, new_user)
        for change in schema_changes:
            click.echo(f"{change.path}: {change.change_type} breaking={change.breaking}")

        old_api = APIContract("users", "/users/{id}", "GET", "1.2.0", old_user, schemas.infer_from_sample("Error", "1.0.0", {"error": "missing"}), True)
        new_api = APIContract("users", "/users/{id}", "GET", "1.3.0", new_user, schemas.infer_from_sample("Error", "1.0.0", {"message": "missing"}), False)
        for drift in APIContractMonitor().compare(old_api, new_api):
            click.echo(f"{drift.contract_key} {drift.area}: {drift.message} breaking={drift.breaking}")

        semver = SemVerEnforcer().validate("1.2.0", "1.3.0", schema_changes)
        click.echo(f"Semver: {semver.reason} valid={semver.valid}")

        config_drifts = ConfigurationDriftTracker().compare({"staging": {"feature_flag": False}, "production": {"feature_flag": True}}, {"feature_flag"})
        for drift in config_drifts:
            click.echo(f"Config: {drift.key} {drift.environments} severity={drift.severity}")

        test_invariants = TestInvariantMiner().mine(root)
        click.echo(f"Test-inferred invariants: {len(test_invariants)}")

        debt_total = DebtQuantifier().total(incidents)
        click.echo(f"Debt estimate: {debt_total.hours:.1f}h ${debt_total.dollars:.2f}")

        reports = TeamDriftReporter().build(incidents, {"api/": "Team Alpha", "services/": "Team Beta", "migrations/": "Platform"})
        for report in reports:
            click.echo(f"Team: {report.team} incidents={report.incidents} dollars=${report.estimated_dollars:.2f}")

        graph_lines = InvariantGraphVisualizer().to_dot(invariants, incidents).splitlines()
        click.echo(f"Invariant graph: {len(graph_lines)} DOT lines")


def _record_and_print_drifts(db: SyncGuardDB, incidents: list[DriftIncident]) -> None:
    db.save_drifts(incidents)
    debt_entries = DriftLedger().build_debt(db.list_drifts())
    db.save_debt(debt_entries)
    click.echo(f"Detected {len(incidents)} drift incidents")
    _print_drifts(incidents)


def _print_invariants(invariants: Iterable[Invariant]) -> None:
    for inv in invariants:
        click.echo(f"{inv.id} [{inv.invariant_type}] {inv.name} confidence={inv.confidence:.2f}")
        click.echo(f"  scope={inv.scope} files={', '.join(inv.source_files)}")


def _print_drifts(drifts: Iterable[DriftIncident]) -> None:
    for drift in drifts:
        click.echo(f"{drift.id} severity={drift.severity} impact={drift.impact_score:.2f} file={drift.file_path}")
        if drift.affected_files:
            click.echo(f"  affects: {', '.join(drift.affected_files)}")
        click.echo(f"  fix: {drift.suggested_fix}")


def _create_demo_project(root: Path) -> None:
    for directory in ["api", "services", "migrations"]:
        (root / directory).mkdir(parents=True, exist_ok=True)
    (root / "api" / "models.py").write_text(
        "from dataclasses import dataclass\n\n@dataclass\nclass User:\n    user_id: str\n    email: str\n",
        encoding="utf-8",
    )
    (root / "api" / "events.py").write_text(
        "def publish_user_created(user_id: str) -> dict:\n"
        "    return {'topic': 'user.created', 'user_id': user_id, 'schema_registry': 'v3'}\n",
        encoding="utf-8",
    )
    (root / "api" / "handlers.py").write_text(
        "def get_user_handler():\n    return {'data': {'id': 'u1'}, 'meta': {}, 'links': {}}\n\n"
        "def list_users_handler():\n    return {'data': [], 'meta': {}, 'links': {}}\n\n"
        "def post_user_handler():\n    return {'data': {'ok': True}, 'meta': {}, 'links': {}}\n",
        encoding="utf-8",
    )
    (root / "services" / "payment.py").write_text(
        "def consume_payment(user_id: str) -> None:\n    assert isinstance(user_id, str)\n",
        encoding="utf-8",
    )
    (root / "services" / "notification.py").write_text(
        "def consume_notification(user_id: str) -> None:\n    assert isinstance(user_id, str)\n",
        encoding="utf-8",
    )
    (root / "migrations" / "001_create_users.py").write_text(
        "def up():\n    create_table = True\n    return create_table\n\n"
        "def down():\n    drop_table = True\n    return drop_table\n",
        encoding="utf-8",
    )
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "tests" / "test_api.py").write_text(
        "def test_user_response_contract():\n"
        "    response = {'data': {'id': 'u1'}, 'meta': {}, 'links': {}}\n"
        "    assert 'data' in response\n"
        "    assert response['meta'] == {}\n",
        encoding="utf-8",
    )


def _introduce_demo_drift(root: Path) -> None:
    (root / "api" / "models.py").write_text(
        "from dataclasses import dataclass\n\n@dataclass\nclass User:\n    user_id: int\n    email: str\n",
        encoding="utf-8",
    )
    (root / "api" / "handlers.py").write_text(
        "def get_user_handler():\n    return {'result': {'id': 'u1'}}\n\n"
        "def list_users_handler():\n    return {'data': [], 'meta': {}, 'links': {}}\n\n"
        "def post_user_handler():\n    return {'data': {'ok': True}, 'meta': {}, 'links': {}}\n",
        encoding="utf-8",
    )
    (root / "migrations" / "001_create_users.py").write_text(
        "def up():\n    create_table = True\n    return create_table\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path

from syncguard.detector.detector import DriftDetector
from syncguard.detector.git_diff import parse_diff
from syncguard.extractor.extractor import InvariantExtractor


def test_parse_diff() -> None:
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-x: str\n+x: int\n"
    changed = parse_diff(diff)
    assert changed[0].path == "a.py"
    assert changed[0].added_lines == ["x: int"]
    assert changed[0].removed_lines == ["x: str"]


def test_detects_user_id_type_drift(sample_project: Path) -> None:
    invariants = InvariantExtractor().extract(sample_project)
    diff = "diff --git a/api/models.py b/api/models.py\n--- a/api/models.py\n+++ b/api/models.py\n@@ -4 +4 @@\n-    user_id: str\n+    user_id: int\n"
    incidents = DriftDetector(invariants, sample_project).check_diff(diff)
    assert any(incident.file_path == "api/models.py" and incident.severity in {"medium", "high", "critical"} for incident in incidents)


def test_detects_response_shape_drift(sample_project: Path) -> None:
    invariants = InvariantExtractor().extract(sample_project)
    diff = "diff --git a/api/handlers.py b/api/handlers.py\n--- a/api/handlers.py\n+++ b/api/handlers.py\n@@ -1 +1 @@\n-    return {'data': {}, 'meta': {}, 'links': {}}\n+    return {'result': {}}\n"
    incidents = DriftDetector(invariants, sample_project).check_diff(diff)
    assert any("dictionary" in incident.suggested_fix for incident in incidents)


def test_detects_missing_down(sample_project: Path) -> None:
    (sample_project / "migrations" / "001_create_users.py").write_text("def up():\n    pass\n", encoding="utf-8")
    invariants = InvariantExtractor().extract(sample_project)
    # Recreate invariant from pre-drift state by forcing the expected evidence.
    from syncguard.core.models import Invariant

    inv = Invariant(
        "Migrations define reversible down()",
        "Migration files are expected to define both up() and down().",
        "behavioral",
        "migrations",
        ["migrations/001_create_users.py"],
        1.0,
        {"required_functions": ["up", "down"]},
    )
    diff = "diff --git a/migrations/001_create_users.py b/migrations/001_create_users.py\n--- a/migrations/001_create_users.py\n+++ b/migrations/001_create_users.py\n@@ -1,4 +1,2 @@\n def up():\n     pass\n-def down():\n-    pass\n"
    incidents = DriftDetector([*invariants, inv], sample_project).check_diff(diff)
    assert any("down()" in incident.suggested_fix for incident in incidents)

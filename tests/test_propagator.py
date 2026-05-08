from __future__ import annotations

from syncguard.core.models import Invariant
from syncguard.propagator.propagator import ImpactPropagator


def test_impact_uses_affected_files() -> None:
    inv = Invariant("n", "d", "cross_module", "user_id", ["a.py", "b.py"], 1.0, {"examples": [{"file": "c.py"}]})
    prop = ImpactPropagator()
    assert prop.affected_files(inv, "a.py") == ["b.py", "c.py"]
    assert prop.impact_score(inv, "a.py") >= 0.7


def test_severity_thresholds() -> None:
    prop = ImpactPropagator()
    assert prop.severity(0.9) == "critical"
    assert prop.severity(0.7) == "high"
    assert prop.severity(0.5) == "medium"
    assert prop.severity(0.2) == "low"

from __future__ import annotations

from syncguard.core.models import Invariant
from syncguard.fixer.fixer import AutoFixSuggester


def test_type_fix() -> None:
    inv = Invariant("n", "d", "type_contract", "user_id", ["a.py"], 1.0, {"field": "user_id", "expected_type": "str"})
    assert "user_id" in AutoFixSuggester().suggest(inv, "a.py")


def test_data_shape_fix() -> None:
    inv = Invariant("n", "d", "data_shape", "a.py", ["a.py"], 1.0, {"shape": ["data", "meta"]})
    assert "data" in AutoFixSuggester().suggest(inv, "a.py")

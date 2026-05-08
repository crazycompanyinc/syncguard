"""Semantic versioning enforcement for contract changes."""

from __future__ import annotations

from dataclasses import dataclass

from syncguard.v2.schema import SchemaChange


@dataclass(slots=True)
class SemVerDecision:
    required_bump: str
    actual_bump: str
    valid: bool
    reason: str


class SemVerEnforcer:
    """Map detected changes to the minimum semantic version bump."""

    def required_bump(self, changes: list[SchemaChange]) -> str:
        if any(change.breaking for change in changes):
            return "major"
        if any(change.change_type == "added_field" for change in changes):
            return "minor"
        return "patch"

    def validate(self, old_version: str, new_version: str, changes: list[SchemaChange]) -> SemVerDecision:
        required = self.required_bump(changes)
        actual = _actual_bump(old_version, new_version)
        order = {"patch": 0, "minor": 1, "major": 2}
        valid = order[actual] >= order[required]
        return SemVerDecision(required, actual, valid, f"{required} bump required, {actual} bump provided")


def _actual_bump(old_version: str, new_version: str) -> str:
    old = [int(part) for part in old_version.split(".")[:3]]
    new = [int(part) for part in new_version.split(".")[:3]]
    if new[0] > old[0]:
        return "major"
    if new[1] > old[1]:
        return "minor"
    return "patch"

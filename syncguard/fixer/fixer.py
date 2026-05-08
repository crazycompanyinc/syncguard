"""Deterministic suggested fixes for drift incidents."""

from __future__ import annotations

from syncguard.core.models import Invariant


class AutoFixSuggester:
    """Generate text fixes from invariant evidence."""

    def suggest(self, invariant: Invariant, file_path: str) -> str:
        if invariant.invariant_type in {"type_contract", "cross_module"}:
            field = invariant.evidence.get("field", invariant.scope)
            expected = invariant.evidence.get("expected_type")
            return f"Restore `{field}` in `{file_path}` to `{expected}` or update every dependent module consistently."
        if invariant.invariant_type == "data_shape":
            shape = invariant.evidence.get("shape", [])
            keys = ", ".join(repr(key) for key in shape)
            return f"Return a dictionary with keys {{{keys}}} in `{file_path}` to match the established API shape."
        if invariant.invariant_type == "behavioral":
            required = invariant.evidence.get("required_functions")
            if required:
                return f"Add the missing `{required[-1]}()` implementation in `{file_path}` and make it reverse `up()`."
            call = invariant.evidence.get("call")
            return f"Restore the required `{call}` call in `{file_path}` before the protected operation."
        if invariant.invariant_type == "convention":
            return f"Rename or relocate `{file_path}` so it follows the established `{invariant.evidence.get('pattern')}` convention."
        if invariant.invariant_type == "schema_evolution":
            return f"Restore schema `{invariant.scope}` compatibility in `{file_path}` or publish a coordinated major version."
        if invariant.invariant_type == "api_contract":
            return f"Restore the API contract for `{invariant.scope}` in `{file_path}` or notify consumers with a major version bump."
        if invariant.invariant_type == "database_schema":
            return f"Keep database columns used by application code in `{file_path}` or migrate callers before merging."
        if invariant.invariant_type == "configuration":
            return f"Align `{file_path}` with the expected environment configuration values."
        if invariant.invariant_type == "test_inferred":
            return f"Preserve the behavior assumed by tests for `{invariant.scope}` or update the tests and consumers together."
        return f"Update `{file_path}` so it satisfies invariant `{invariant.name}`."

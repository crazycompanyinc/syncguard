"""Deterministic code fix generation for common drift classes."""

from __future__ import annotations

from dataclasses import dataclass

from syncguard.core.models import DriftIncident, Invariant


@dataclass(slots=True)
class CodeFix:
    file_path: str
    description: str
    original: str
    patched: str


class AutoFixGenerator:
    """Generate concrete patched content for supported invariants."""

    def generate(self, invariant: Invariant, incident: DriftIncident, content: str) -> CodeFix | None:
        if invariant.invariant_type in {"type_contract", "cross_module"}:
            return self._fix_type(invariant, incident, content)
        if invariant.invariant_type == "data_shape":
            return self._fix_shape(invariant, incident, content)
        if invariant.invariant_type == "configuration":
            return self._fix_config(invariant, incident, content)
        return None

    def _fix_type(self, invariant: Invariant, incident: DriftIncident, content: str) -> CodeFix | None:
        field = invariant.evidence.get("field", invariant.scope)
        expected = invariant.evidence.get("expected_type")
        if not field or not expected:
            return None
        patched = content.replace(f"{field}: int", f"{field}: {expected}").replace(f"{field}: float", f"{field}: {expected}")
        if patched == content:
            return None
        return CodeFix(incident.file_path, f"Restore `{field}` annotation to `{expected}`.", content, patched)

    def _fix_shape(self, invariant: Invariant, incident: DriftIncident, content: str) -> CodeFix | None:
        shape = invariant.evidence.get("shape", [])
        if not shape:
            return None
        replacement = "{" + ", ".join(f"{key!r}: {{}}" for key in shape) + "}"
        patched_lines = []
        changed = False
        for line in content.splitlines():
            if "return" in line and "{" in line:
                prefix = line.split("return", 1)[0]
                patched_lines.append(f"{prefix}return {replacement}")
                changed = True
            else:
                patched_lines.append(line)
        if not changed:
            return None
        return CodeFix(incident.file_path, "Restore response dictionary shape.", content, "\n".join(patched_lines) + ("\n" if content.endswith("\n") else ""))

    def _fix_config(self, invariant: Invariant, incident: DriftIncident, content: str) -> CodeFix | None:
        key = invariant.evidence.get("key")
        expected = invariant.evidence.get("expected")
        if key is None or expected is None:
            return None
        patched_lines = []
        changed = False
        for line in content.splitlines():
            if line.strip().startswith(f"{key}="):
                patched_lines.append(f"{key}={expected}")
                changed = True
            else:
                patched_lines.append(line)
        if not changed:
            return None
        return CodeFix(incident.file_path, f"Set `{key}` to `{expected}`.", content, "\n".join(patched_lines) + ("\n" if content.endswith("\n") else ""))

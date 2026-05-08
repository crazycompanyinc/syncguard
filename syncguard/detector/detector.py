"""Drift detection against extracted invariants."""

from __future__ import annotations

import ast
from pathlib import Path

from syncguard.core.models import DriftIncident, Invariant
from syncguard.detector.git_diff import ChangedFile, git_diff, parse_diff
from syncguard.fixer.fixer import AutoFixSuggester
from syncguard.propagator.propagator import ImpactPropagator


class DriftDetector:
    """Compare diffs and current files against known invariants."""

    def __init__(
        self,
        invariants: list[Invariant],
        root: str | Path = ".",
        propagator: ImpactPropagator | None = None,
        fixer: AutoFixSuggester | None = None,
    ) -> None:
        self.invariants = invariants
        self.root = Path(root).resolve()
        self.propagator = propagator or ImpactPropagator()
        self.fixer = fixer or AutoFixSuggester()

    def check_git(self, staged: bool = False) -> list[DriftIncident]:
        return self.check_diff(git_diff(self.root, staged=staged))

    def check_diff_file(self, diff_file: str | Path) -> list[DriftIncident]:
        return self.check_diff(Path(diff_file).read_text(encoding="utf-8"))

    def check_diff(self, diff_text: str) -> list[DriftIncident]:
        changed_files = parse_diff(diff_text)
        incidents: list[DriftIncident] = []
        for changed in changed_files:
            for invariant in self._candidate_invariants(changed):
                if self._violates(changed, invariant):
                    impact = self.propagator.impact_score(invariant, changed.path)
                    incidents.append(
                        DriftIncident(
                            invariant_id=invariant.id,
                            file_path=changed.path,
                            diff_excerpt=changed.excerpt,
                            severity=self.propagator.severity(impact),  # type: ignore[arg-type]
                            drift_type="new_violation",
                            status="open",
                            impact_score=impact,
                            affected_files=self.propagator.affected_files(invariant, changed.path),
                            suggested_fix=self.fixer.suggest(invariant, changed.path),
                        )
                    )
        return incidents

    def _candidate_invariants(self, changed: ChangedFile) -> list[Invariant]:
        candidates = []
        for inv in self.invariants:
            if changed.path in inv.source_files or inv.scope in changed.path or inv.scope in changed.excerpt:
                candidates.append(inv)
            elif inv.evidence.get("field") and inv.evidence["field"] in changed.excerpt:
                candidates.append(inv)
        return candidates

    def _violates(self, changed: ChangedFile, invariant: Invariant) -> bool:
        if invariant.invariant_type in {"type_contract", "cross_module"}:
            return self._type_contract_violated(changed, invariant)
        if invariant.invariant_type == "data_shape":
            return self._data_shape_violated(changed, invariant)
        if invariant.invariant_type == "behavioral":
            return self._behavioral_violated(changed, invariant)
        if invariant.invariant_type == "convention":
            return self._convention_violated(changed, invariant)
        return False

    def _type_contract_violated(self, changed: ChangedFile, invariant: Invariant) -> bool:
        field = invariant.evidence.get("field", invariant.scope)
        expected = invariant.evidence.get("expected_type")
        if not field or not expected:
            return False
        for line in changed.added_lines:
            stripped = line.strip()
            if f"{field}:" in stripped and f"{field}: {expected}" not in stripped:
                return True
            if f'"{field}"' in stripped or f"'{field}'" in stripped:
                if expected == "str" and any(token in stripped for token in ("int(", ": int", "-> int")):
                    return True
        return False

    def _data_shape_violated(self, changed: ChangedFile, invariant: Invariant) -> bool:
        expected = set(invariant.evidence.get("shape", []))
        if not expected:
            return False
        for line in changed.added_lines:
            if "return" in line and "{" in line:
                keys = _literal_dict_keys(line)
                if keys and keys != expected:
                    return True
        return False

    def _behavioral_violated(self, changed: ChangedFile, invariant: Invariant) -> bool:
        required = invariant.evidence.get("required_functions")
        if required and "down" in required:
            file_path = self.root / changed.path
            if file_path.exists():
                try:
                    tree = ast.parse(file_path.read_text(encoding="utf-8"))
                except (OSError, SyntaxError, UnicodeDecodeError):
                    return False
                funcs = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
                return "up" in funcs and "down" not in funcs
            return any("def down" in line for line in changed.removed_lines)
        call = invariant.evidence.get("call")
        if call:
            return any(call in line for line in changed.removed_lines) and not any(call in line for line in changed.added_lines)
        return False

    def _convention_violated(self, changed: ChangedFile, invariant: Invariant) -> bool:
        pattern = invariant.evidence.get("pattern")
        name = Path(changed.path).name
        if pattern == "test_prefix":
            return "/tests/" in f"/{changed.path}" and not name.startswith("test_")
        if pattern == "test_suffix":
            return "/tests/" in f"/{changed.path}" and "_test." not in name
        if pattern == "service_suffix":
            return "service" in changed.path and "_service." not in name
        return False


def _literal_dict_keys(line: str) -> set[str]:
    try:
        expr = line.split("return", 1)[1].strip()
        node = ast.parse(expr, mode="eval").body
    except SyntaxError:
        return set()
    if not isinstance(node, ast.Dict):
        return set()
    keys: set[str] = set()
    for key in node.keys:
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            keys.add(key.value)
    return keys

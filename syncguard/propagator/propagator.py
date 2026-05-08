"""Impact estimation for drift incidents."""

from __future__ import annotations

from syncguard.core.models import Invariant


class ImpactPropagator:
    """Estimate affected files and severity from invariant evidence."""

    def affected_files(self, invariant: Invariant, changed_file: str) -> list[str]:
        files = set(invariant.source_files)
        for example in invariant.evidence.get("examples", []):
            file_path = example.get("file") if isinstance(example, dict) else None
            if file_path:
                files.add(file_path)
        files.discard(changed_file)
        return sorted(files)

    def impact_score(self, invariant: Invariant, changed_file: str) -> float:
        affected = self.affected_files(invariant, changed_file)
        base = min(1.0, 0.25 + 0.15 * len(affected))
        type_weight = {
            "cross_module": 0.25,
            "type_contract": 0.2,
            "data_shape": 0.15,
            "behavioral": 0.1,
            "convention": 0.0,
        }[invariant.invariant_type]
        return round(min(1.0, base + type_weight), 2)

    def severity(self, impact_score: float) -> str:
        if impact_score >= 0.85:
            return "critical"
        if impact_score >= 0.65:
            return "high"
        if impact_score >= 0.4:
            return "medium"
        return "low"

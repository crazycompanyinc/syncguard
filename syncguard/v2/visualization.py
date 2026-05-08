"""Invariant graph visualization."""

from __future__ import annotations

from syncguard.core.models import DriftIncident, Invariant


class InvariantGraphVisualizer:
    """Render invariants and affected files as Graphviz DOT."""

    def to_dot(self, invariants: list[Invariant], drifts: list[DriftIncident] | None = None) -> str:
        drifting = {drift.invariant_id for drift in drifts or [] if drift.status == "open"}
        lines = ["digraph syncguard {", '  rankdir="LR";']
        for invariant in invariants:
            color = "red" if invariant.id in drifting else "green"
            lines.append(f'  "{invariant.id}" [label="{_escape(invariant.name)}", color="{color}", shape="box"];')
            for file_path in invariant.source_files:
                lines.append(f'  "{_escape(file_path)}" [shape="ellipse"];')
                lines.append(f'  "{invariant.id}" -> "{_escape(file_path)}";')
        lines.append("}")
        return "\n".join(lines)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')

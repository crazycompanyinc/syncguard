"""Schema evolution tracking and consumer compatibility checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from syncguard.core.models import Invariant


@dataclass(slots=True)
class SchemaChange:
    path: str
    change_type: str
    old: Any
    new: Any
    breaking: bool
    reason: str


@dataclass(slots=True)
class SchemaVersion:
    name: str
    version: str
    fields: dict[str, str]
    required: set[str] = field(default_factory=set)


class SchemaEvolutionTracker:
    """Track field-level schema changes over time."""

    def infer_from_sample(self, name: str, version: str, sample: dict[str, Any], required: set[str] | None = None) -> SchemaVersion:
        return SchemaVersion(name=name, version=version, fields={key: _type_name(value) for key, value in sample.items()}, required=required or set(sample))

    def compare(self, old: SchemaVersion, new: SchemaVersion) -> list[SchemaChange]:
        changes: list[SchemaChange] = []
        for field_name, old_type in sorted(old.fields.items()):
            if field_name not in new.fields:
                changes.append(SchemaChange(field_name, "removed_field", old_type, None, field_name in old.required, "required consumer field removed"))
            elif new.fields[field_name] != old_type:
                changes.append(SchemaChange(field_name, "type_changed", old_type, new.fields[field_name], True, "field type changed"))
        for field_name, new_type in sorted(new.fields.items()):
            if field_name not in old.fields:
                required = field_name in new.required
                changes.append(SchemaChange(field_name, "added_field", None, new_type, required, "new required field" if required else "new optional field"))
        return changes

    def downstream_breakages(self, changes: list[SchemaChange], consumers: dict[str, set[str]]) -> dict[str, list[str]]:
        breaking_paths = {change.path for change in changes if change.breaking}
        return {
            consumer: sorted(fields & breaking_paths)
            for consumer, fields in consumers.items()
            if fields & breaking_paths
        }

    def invariant_for(self, schema: SchemaVersion, source_file: str) -> Invariant:
        return Invariant(
            name=f"{schema.name} schema {schema.version}",
            description=f"Schema `{schema.name}` exposes stable fields and types.",
            invariant_type="schema_evolution",
            scope=schema.name,
            source_files=[source_file],
            confidence=1.0,
            evidence={"version": schema.version, "fields": schema.fields, "required": sorted(schema.required)},
        )


def _type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return type(value).__name__

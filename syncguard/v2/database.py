"""Database schema drift detection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(slots=True)
class TableSchema:
    name: str
    columns: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class DatabaseDrift:
    table: str
    column: str
    breaking: bool
    message: str


class DatabaseSchemaDriftMonitor:
    """Compare database schema changes against application column assumptions."""

    def parse_create_table(self, sql: str) -> TableSchema:
        match = re.search(r"CREATE\s+TABLE\s+(\w+)\s*\((.*)\)", sql, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            raise ValueError("SQL does not contain a CREATE TABLE statement")
        table = TableSchema(match.group(1))
        for raw_column in match.group(2).split(","):
            parts = raw_column.strip().split()
            if len(parts) >= 2 and parts[0].lower() not in {"primary", "foreign", "unique", "constraint"}:
                table.columns[parts[0]] = parts[1].lower()
        return table

    def compare(self, old: TableSchema, new: TableSchema, app_assumptions: dict[str, set[str]]) -> list[DatabaseDrift]:
        required = app_assumptions.get(old.name, set())
        drifts: list[DatabaseDrift] = []
        for column, old_type in sorted(old.columns.items()):
            if column not in new.columns:
                drifts.append(DatabaseDrift(old.name, column, column in required, "column removed"))
            elif new.columns[column] != old_type:
                drifts.append(DatabaseDrift(old.name, column, column in required, "column type changed"))
        return drifts

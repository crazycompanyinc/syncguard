"""SQLite persistence for SyncGuard."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from syncguard.core.models import DriftDebtEntry, DriftIncident, Invariant

DEFAULT_DB_NAME = ".syncguard/syncguard.db"


class SyncGuardDB:
    """Small SQLite repository storing JSON-serialized records."""

    def __init__(self, root: str | Path = ".", db_path: str | Path | None = None) -> None:
        self.root = Path(root)
        self.db_path = Path(db_path) if db_path else self.root / DEFAULT_DB_NAME
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS invariants (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS drifts (
                    id TEXT PRIMARY KEY,
                    invariant_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    resolved_at TEXT,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS debt (
                    file_path TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );
                """
            )

    def clear_invariants(self) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM invariants")

    def save_invariants(self, invariants: Iterable[Invariant]) -> None:
        with self.connect() as conn:
            for inv in invariants:
                conn.execute(
                    "INSERT OR REPLACE INTO invariants (id, payload) VALUES (?, ?)",
                    (inv.id, json.dumps(inv.to_dict(), sort_keys=True)),
                )

    def list_invariants(self, invariant_type: str | None = None) -> list[Invariant]:
        with self.connect() as conn:
            rows = conn.execute("SELECT payload FROM invariants ORDER BY id").fetchall()
        invariants = [Invariant.from_dict(json.loads(row["payload"])) for row in rows]
        if invariant_type:
            invariants = [inv for inv in invariants if inv.invariant_type == invariant_type]
        return invariants

    def save_drifts(self, drifts: Iterable[DriftIncident]) -> None:
        with self.connect() as conn:
            for drift in drifts:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO drifts
                    (id, invariant_id, file_path, status, detected_at, resolved_at, payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        drift.id,
                        drift.invariant_id,
                        drift.file_path,
                        drift.status,
                        drift.detected_at,
                        drift.resolved_at,
                        json.dumps(drift.to_dict(), sort_keys=True),
                    ),
                )

    def list_drifts(self, status: str | None = None) -> list[DriftIncident]:
        sql = "SELECT payload FROM drifts"
        params: tuple[str, ...] = ()
        if status:
            sql += " WHERE status = ?"
            params = (status,)
        sql += " ORDER BY detected_at DESC"
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [DriftIncident.from_dict(json.loads(row["payload"])) for row in rows]

    def get_drift(self, drift_id: str) -> DriftIncident | None:
        with self.connect() as conn:
            row = conn.execute("SELECT payload FROM drifts WHERE id = ?", (drift_id,)).fetchone()
        return DriftIncident.from_dict(json.loads(row["payload"])) if row else None

    def save_debt(self, entries: Iterable[DriftDebtEntry]) -> None:
        with self.connect() as conn:
            for entry in entries:
                conn.execute(
                    "INSERT OR REPLACE INTO debt (file_path, payload) VALUES (?, ?)",
                    (entry.file_path, json.dumps(entry.to_dict(), sort_keys=True)),
                )

    def list_debt(self, file_path: str | None = None) -> list[DriftDebtEntry]:
        sql = "SELECT payload FROM debt"
        params: tuple[str, ...] = ()
        if file_path:
            sql += " WHERE file_path = ?"
            params = (file_path,)
        sql += " ORDER BY file_path"
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [DriftDebtEntry.from_dict(json.loads(row["payload"])) for row in rows]

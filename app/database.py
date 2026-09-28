"""Lightweight SQLite persistence for generated plans.

Uses Python's built-in ``sqlite3`` so there are no extra native dependencies.
The database file is derived from ``DATABASE_URL`` (default ``fitbuddy.db``).
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import DATABASE_URL


def _db_path() -> Path:
    """Resolve the sqlite file path from a ``sqlite:///./file.db`` style URL."""
    url = DATABASE_URL
    if url.startswith("sqlite:///"):
        raw = url[len("sqlite:///") :]
    elif url.startswith("sqlite://"):
        raw = url[len("sqlite://") :]
    else:
        # Unknown scheme - fall back to a local file so the app still runs.
        raw = "./fitbuddy.db"
    return Path(raw).resolve()


DB_PATH = _db_path()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they do not exist. Safe to call on every startup."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                name TEXT,
                goal TEXT,
                source TEXT,
                request_json TEXT NOT NULL,
                plan_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_plan(name: str, goal: str, source: str, request: dict, plan: dict) -> int:
    """Persist a generated plan and return its row id."""
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO plans (created_at, name, goal, source, request_json, plan_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                name,
                goal,
                source,
                json.dumps(request),
                json.dumps(plan),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_plans(limit: int = 50) -> list[dict]:
    """Return recent plans, newest first (metadata only)."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, name, goal, source
            FROM plans
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

"""SQLite persistence for jobs and analyses.

A job tracks the background work for one submitted source. A completed job
points at an analysis, which holds the transcript and generated notes. Later
features (uploads, history, deletion, chat) extend these tables.
"""

import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    action_items TEXT NOT NULL,
    key_decisions TEXT NOT NULL,
    open_questions TEXT NOT NULL,
    transcript TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    source_kind TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    step TEXT,
    error TEXT,
    analysis_id TEXT REFERENCES analyses(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

JOB_FIELDS = (
    "id", "source_kind", "source", "status", "step", "error",
    "analysis_id", "created_at", "updated_at",
)
ANALYSIS_FIELDS = (
    "id", "title", "summary", "action_items", "key_decisions",
    "open_questions", "transcript", "created_at",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def _execute(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
            self._conn.commit()
        return rows

    def create_job(self, source_kind: str, source: str) -> dict:
        job_id, now = uuid.uuid4().hex, _now()
        self._execute(
            "INSERT INTO jobs (id, source_kind, source, status, created_at, updated_at)"
            " VALUES (?, ?, ?, 'queued', ?, ?)",
            (job_id, source_kind, source, now, now),
        )
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> dict | None:
        rows = self._execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        return dict(rows[0]) if rows else None

    def update_job(self, job_id: str, **fields: str | None) -> None:
        assert set(fields) <= set(JOB_FIELDS)
        fields["updated_at"] = _now()
        assignments = ", ".join(f"{name} = ?" for name in fields)
        self._execute(
            f"UPDATE jobs SET {assignments} WHERE id = ?", (*fields.values(), job_id)
        )

    def fail_unfinished_jobs(self, reason: str) -> None:
        self._execute(
            "UPDATE jobs SET status = 'failed', step = NULL, error = ?, updated_at = ?"
            " WHERE status IN ('queued', 'processing')",
            (reason, _now()),
        )

    def create_analysis(self, **notes: str) -> dict:
        analysis_id = uuid.uuid4().hex
        self._execute(
            "INSERT INTO analyses (id, title, summary, action_items, key_decisions,"
            " open_questions, transcript, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                analysis_id, notes["title"], notes["summary"], notes["action_items"],
                notes["key_decisions"], notes["open_questions"], notes["transcript"],
                _now(),
            ),
        )
        return self.get_analysis(analysis_id)

    def get_analysis(self, analysis_id: str) -> dict | None:
        rows = self._execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,))
        return dict(rows[0]) if rows else None

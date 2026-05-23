from __future__ import annotations

import json
import time
from threading import RLock
from typing import Any

from app.storage import SQLiteDatabase, SQLiteRow


class DownloadManagerRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database
        self._lock = RLock()
        self._ensure_schema()

    def load_settings(self) -> dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM download_manager_settings").fetchall()
        return {str(row["key"]): str(row["value"] or "") for row in rows}

    def save_settings(self, settings: dict[str, object]) -> None:
        with self._connect() as conn:
            for key, value in settings.items():
                conn.execute(
                    """
                    INSERT INTO download_manager_settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = excluded.updated_at
                    """,
                    (str(key), str(value), self._now_ms()),
                )

    def list_tasks(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM download_manager_tasks
                ORDER BY created_at ASC, updated_at ASC
                """
            ).fetchall()
        tasks: list[dict] = []
        for row in rows:
            try:
                payload = json.loads(str(row["payload_json"] or "{}"))
            except json.JSONDecodeError:
                payload = {}
            if isinstance(payload, dict) and payload.get("id"):
                tasks.append(payload)
        return tasks

    def upsert_task(self, task: dict) -> None:
        task_id = str(task.get("id") or "")
        if not task_id:
            return
        now = self._now_ms()
        created = _timestamp_from_text(str(task.get("createdAt") or "")) or now
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO download_manager_tasks (id, url, state, created_at, updated_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    url = excluded.url,
                    state = excluded.state,
                    updated_at = excluded.updated_at,
                    payload_json = excluded.payload_json
                """,
                (
                    task_id,
                    str(task.get("url") or ""),
                    str(task.get("state") or ""),
                    created,
                    now,
                    json.dumps(task, ensure_ascii=False, separators=(",", ":")),
                ),
            )

    def delete_task(self, task_id: str) -> None:
        if not task_id:
            return
        with self._connect() as conn:
            conn.execute("DELETE FROM download_manager_tasks WHERE id = ?", (str(task_id),))

    def clear_tasks(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM download_manager_tasks")

    def delete_tasks_by_states(self, states: set[str]) -> None:
        clean = [str(state) for state in states if state]
        if not clean:
            return
        placeholders = ",".join("?" for _ in clean)
        with self._connect() as conn:
            conn.execute(f"DELETE FROM download_manager_tasks WHERE state IN ({placeholders})", tuple(clean))

    def _connect(self):
        return _LockedConnection(self._database, self._lock)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS download_manager_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL DEFAULT '',
                    updated_at INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS download_manager_tasks (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL DEFAULT '',
                    state TEXT NOT NULL DEFAULT '',
                    created_at INTEGER NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_download_manager_tasks_state ON download_manager_tasks(state)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_download_manager_tasks_created ON download_manager_tasks(created_at)")

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)


class _LockedConnection:
    def __init__(self, database: SQLiteDatabase, lock: RLock) -> None:
        self._database = database
        self._lock = lock
        self._ctx = None
        self._conn = None

    def __enter__(self):
        self._lock.acquire()
        try:
            self._ctx = self._database.connection(row_factory=SQLiteRow)
            self._conn = self._ctx.__enter__()
        except Exception:
            self._lock.release()
            raise
        return self._conn

    def __exit__(self, exc_type: Any, exc: Any, tb: Any):
        try:
            return self._ctx.__exit__(exc_type, exc, tb)
        finally:
            self._lock.release()


def _timestamp_from_text(value: str) -> int:
    text = value.strip()
    if not text:
        return 0
    try:
        return int(time.mktime(time.strptime(text, "%Y-%m-%d %H:%M:%S")) * 1000)
    except ValueError:
        return 0

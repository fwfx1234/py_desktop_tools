from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Iterable, Literal

from app.storage import SQLiteDatabase, SQLiteRow


ActionKind = Literal["script", "open_path", "open_url"]
ScriptType = Literal["shell", "node", "python", "other"]
FeedbackMode = Literal["silent", "popup", "notification"]
RunStatus = Literal["success", "failed", "timeout", "error"]

STDIO_LIMIT_BYTES = 64 * 1024


@dataclass(slots=True)
class QuickLaunchAction:
    id: int
    name: str
    description: str = ""
    kind: ActionKind = "script"
    script_type: ScriptType = "shell"
    interpreter: str = ""
    path: str = ""
    url: str = ""
    args: str = ""
    cwd: str = ""
    env: dict[str, str] = field(default_factory=dict)
    keywords: list[str] = field(default_factory=list)
    prefixes: list[str] = field(default_factory=list)
    icon: str = ""
    feedback_mode: FeedbackMode = "notification"
    timeout_sec: int = 300
    enabled: bool = True
    sort_order: int = 0
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "kind": self.kind,
            "scriptType": self.script_type,
            "interpreter": self.interpreter,
            "path": self.path,
            "url": self.url,
            "args": self.args,
            "cwd": self.cwd,
            "env": dict(self.env),
            "keywords": list(self.keywords),
            "prefixes": list(self.prefixes),
            "icon": self.icon,
            "feedbackMode": self.feedback_mode,
            "timeoutSec": self.timeout_sec,
            "enabled": self.enabled,
            "sortOrder": self.sort_order,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


@dataclass(slots=True)
class QuickLaunchRun:
    id: int
    action_id: int
    status: RunStatus
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int
    started_at: str
    finished_at: str
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "actionId": self.action_id,
            "status": self.status,
            "exitCode": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "durationMs": self.duration_ms,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "message": self.message,
        }


class QuickLaunchRepository:
    """SQLite storage for actions and run history."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database
        self._lock = RLock()
        self._ensure_schema()

    # ----- actions -----

    def list_actions(self, *, enabled: bool | None = None) -> list[QuickLaunchAction]:
        conditions: list[str] = []
        params: list[object] = []
        if enabled is not None:
            conditions.append("enabled = ?")
            params.append(1 if enabled else 0)
        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM quick_launch_actions
                {where_sql}
                ORDER BY sort_order ASC, id ASC
                """,
                tuple(params),
            ).fetchall()
        return [self._row_to_action(row) for row in rows]

    def get_action(self, action_id: int) -> QuickLaunchAction | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM quick_launch_actions WHERE id = ?", (int(action_id),)
            ).fetchone()
        return self._row_to_action(row) if row is not None else None

    def create_action(
        self,
        *,
        name: str,
        kind: ActionKind = "script",
        script_type: ScriptType = "shell",
        interpreter: str = "",
        description: str = "",
        path: str = "",
        url: str = "",
        args: str = "",
        cwd: str = "",
        env: dict[str, str] | None = None,
        keywords: Iterable[str] | None = None,
        prefixes: Iterable[str] | None = None,
        icon: str = "",
        feedback_mode: FeedbackMode = "notification",
        timeout_sec: int = 300,
        enabled: bool = True,
        sort_order: int | None = None,
    ) -> QuickLaunchAction:
        now = self._now()
        with self._connect() as conn:
            order = (
                sort_order
                if sort_order is not None
                else self._next_sort_order(conn)
            )
            cursor = conn.execute(
                """
                INSERT INTO quick_launch_actions
                    (name, description, kind, script_type, interpreter,
                     path, url, args, cwd, env_json, keywords_json, prefixes_json,
                     icon, feedback_mode, timeout_sec, enabled, sort_order,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name.strip(),
                    description,
                    kind,
                    script_type,
                    interpreter,
                    path,
                    url,
                    args,
                    cwd,
                    json.dumps(env or {}, ensure_ascii=False),
                    json.dumps(list(keywords or []), ensure_ascii=False),
                    json.dumps(list(prefixes or []), ensure_ascii=False),
                    icon,
                    feedback_mode,
                    int(timeout_sec),
                    1 if enabled else 0,
                    int(order),
                    now,
                    now,
                ),
            )
            action_id = int(cursor.lastrowid)
        action = self.get_action(action_id)
        assert action is not None
        return action

    def update_action(self, action_id: int, **fields) -> QuickLaunchAction | None:
        existing = self.get_action(action_id)
        if existing is None:
            return None
        merged = {
            "name": existing.name,
            "description": existing.description,
            "kind": existing.kind,
            "script_type": existing.script_type,
            "interpreter": existing.interpreter,
            "path": existing.path,
            "url": existing.url,
            "args": existing.args,
            "cwd": existing.cwd,
            "env": existing.env,
            "keywords": existing.keywords,
            "prefixes": existing.prefixes,
            "icon": existing.icon,
            "feedback_mode": existing.feedback_mode,
            "timeout_sec": existing.timeout_sec,
            "enabled": existing.enabled,
            "sort_order": existing.sort_order,
        }
        for key, value in fields.items():
            if key in merged:
                merged[key] = value
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE quick_launch_actions
                SET name = ?, description = ?, kind = ?, script_type = ?, interpreter = ?,
                    path = ?, url = ?, args = ?, cwd = ?, env_json = ?, keywords_json = ?,
                    prefixes_json = ?, icon = ?, feedback_mode = ?, timeout_sec = ?,
                    enabled = ?, sort_order = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    str(merged["name"]).strip(),
                    str(merged["description"] or ""),
                    str(merged["kind"]),
                    str(merged["script_type"]),
                    str(merged["interpreter"] or ""),
                    str(merged["path"] or ""),
                    str(merged["url"] or ""),
                    str(merged["args"] or ""),
                    str(merged["cwd"] or ""),
                    json.dumps(merged["env"] or {}, ensure_ascii=False),
                    json.dumps(list(merged["keywords"] or []), ensure_ascii=False),
                    json.dumps(list(merged["prefixes"] or []), ensure_ascii=False),
                    str(merged["icon"] or ""),
                    str(merged["feedback_mode"]),
                    int(merged["timeout_sec"] or 0),
                    1 if merged["enabled"] else 0,
                    int(merged["sort_order"] or 0),
                    now,
                    int(action_id),
                ),
            )
        return self.get_action(action_id)

    def delete_action(self, action_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM quick_launch_actions WHERE id = ?", (int(action_id),)
            )
            return cursor.rowcount > 0

    def set_action_enabled(self, action_id: int, enabled: bool) -> QuickLaunchAction | None:
        return self.update_action(action_id, enabled=bool(enabled))

    # ----- runs -----

    def record_run(
        self,
        *,
        action_id: int,
        status: RunStatus,
        exit_code: int | None,
        stdout: str,
        stderr: str,
        duration_ms: int,
        started_at: str,
        finished_at: str,
        message: str = "",
    ) -> QuickLaunchRun:
        stdout_clean, stdout_truncated = self._truncate(stdout)
        stderr_clean, stderr_truncated = self._truncate(stderr)
        notes: list[str] = []
        if message:
            notes.append(message)
        if stdout_truncated:
            notes.append("stdout truncated")
        if stderr_truncated:
            notes.append("stderr truncated")
        message_final = "; ".join(notes)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO quick_launch_runs
                    (action_id, status, exit_code, stdout, stderr,
                     duration_ms, started_at, finished_at, message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(action_id),
                    status,
                    int(exit_code) if exit_code is not None else None,
                    stdout_clean,
                    stderr_clean,
                    int(duration_ms),
                    started_at,
                    finished_at,
                    message_final,
                ),
            )
            run_id = int(cursor.lastrowid)
        run = self.get_run(run_id)
        assert run is not None
        return run

    def list_runs(self, *, action_id: int | None = None, limit: int = 100) -> list[QuickLaunchRun]:
        conditions: list[str] = []
        params: list[object] = []
        if action_id is not None:
            conditions.append("action_id = ?")
            params.append(int(action_id))
        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(max(1, int(limit)))
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, action_id, status, exit_code, stdout, stderr,
                       duration_ms, started_at, finished_at, message
                FROM quick_launch_runs
                {where_sql}
                ORDER BY id DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [self._row_to_run(row) for row in rows]

    def get_run(self, run_id: int) -> QuickLaunchRun | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, action_id, status, exit_code, stdout, stderr,
                       duration_ms, started_at, finished_at, message
                FROM quick_launch_runs WHERE id = ?
                """,
                (int(run_id),),
            ).fetchone()
        return self._row_to_run(row) if row is not None else None

    def trim_runs(self, *, keep_latest: int = 500) -> int:
        keep = max(0, int(keep_latest))
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM quick_launch_runs").fetchone()
            total = int(row[0]) if row else 0
            if total <= keep:
                return 0
            cursor = conn.execute(
                """
                DELETE FROM quick_launch_runs
                WHERE id IN (
                    SELECT id FROM quick_launch_runs
                    ORDER BY id ASC
                    LIMIT ?
                )
                """,
                (total - keep,),
            )
            return int(cursor.rowcount or 0)

    # ----- internal -----

    def _connect(self):
        return _LockedConnection(self._database, self._lock)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quick_launch_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    kind TEXT NOT NULL DEFAULT 'script',
                    script_type TEXT NOT NULL DEFAULT 'shell',
                    interpreter TEXT NOT NULL DEFAULT '',
                    path TEXT NOT NULL DEFAULT '',
                    url TEXT NOT NULL DEFAULT '',
                    args TEXT NOT NULL DEFAULT '',
                    cwd TEXT NOT NULL DEFAULT '',
                    env_json TEXT NOT NULL DEFAULT '{}',
                    keywords_json TEXT NOT NULL DEFAULT '[]',
                    prefixes_json TEXT NOT NULL DEFAULT '[]',
                    icon TEXT NOT NULL DEFAULT '',
                    feedback_mode TEXT NOT NULL DEFAULT 'notification',
                    timeout_sec INTEGER NOT NULL DEFAULT 300,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ql_actions_enabled ON quick_launch_actions(enabled)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quick_launch_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'success',
                    exit_code INTEGER,
                    stdout TEXT NOT NULL DEFAULT '',
                    stderr TEXT NOT NULL DEFAULT '',
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    started_at TEXT NOT NULL DEFAULT '',
                    finished_at TEXT NOT NULL DEFAULT '',
                    message TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ql_runs_action ON quick_launch_runs(action_id, id DESC)"
            )

    @staticmethod
    def _next_sort_order(conn) -> int:
        row = conn.execute("SELECT COALESCE(MAX(sort_order), -1) FROM quick_launch_actions").fetchone()
        return int(row[0]) + 1 if row else 0

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _truncate(text: str) -> tuple[str, bool]:
        data = (text or "").encode("utf-8", errors="replace")
        if len(data) <= STDIO_LIMIT_BYTES:
            return (text or ""), False
        cut = data[:STDIO_LIMIT_BYTES]
        return cut.decode("utf-8", errors="ignore"), True

    @staticmethod
    def _row_to_action(row: SQLiteRow) -> QuickLaunchAction:
        try:
            env = json.loads(row["env_json"] or "{}")
        except json.JSONDecodeError:
            env = {}
        try:
            keywords = json.loads(row["keywords_json"] or "[]")
        except json.JSONDecodeError:
            keywords = []
        try:
            prefixes = json.loads(row["prefixes_json"] or "[]")
        except json.JSONDecodeError:
            prefixes = []
        return QuickLaunchAction(
            id=int(row["id"]),
            name=str(row["name"] or ""),
            description=str(row["description"] or ""),
            kind=str(row["kind"] or "script"),  # type: ignore[arg-type]
            script_type=str(row["script_type"] or "shell"),  # type: ignore[arg-type]
            interpreter=str(row["interpreter"] or ""),
            path=str(row["path"] or ""),
            url=str(row["url"] or ""),
            args=str(row["args"] or ""),
            cwd=str(row["cwd"] or ""),
            env={str(k): str(v) for k, v in (env or {}).items()},
            keywords=[str(item) for item in (keywords or [])],
            prefixes=[str(item) for item in (prefixes or [])],
            icon=str(row["icon"] or ""),
            feedback_mode=str(row["feedback_mode"] or "notification"),  # type: ignore[arg-type]
            timeout_sec=int(row["timeout_sec"] or 0),
            enabled=bool(row["enabled"]),
            sort_order=int(row["sort_order"] or 0),
            created_at=str(row["created_at"] or ""),
            updated_at=str(row["updated_at"] or ""),
        )

    @staticmethod
    def _row_to_run(row: SQLiteRow) -> QuickLaunchRun:
        return QuickLaunchRun(
            id=int(row["id"]),
            action_id=int(row["action_id"]),
            status=str(row["status"] or "success"),  # type: ignore[arg-type]
            exit_code=int(row["exit_code"]) if row["exit_code"] is not None else None,
            stdout=str(row["stdout"] or ""),
            stderr=str(row["stderr"] or ""),
            duration_ms=int(row["duration_ms"] or 0),
            started_at=str(row["started_at"] or ""),
            finished_at=str(row["finished_at"] or ""),
            message=str(row["message"] or ""),
        )


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

    def __exit__(self, exc_type, exc, tb):
        try:
            return self._ctx.__exit__(exc_type, exc, tb)
        finally:
            self._lock.release()

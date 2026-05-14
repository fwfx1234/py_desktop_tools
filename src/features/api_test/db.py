from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from uuid import uuid4

from app.storage import SQLiteConnection, SQLiteDatabase, sqlite_database


_BODY_MODES = ("none", "x-www-form-urlencoded", "JSON", "XML", "Text", "file")


class ApiDatabase:
    SCHEMA_VERSION = 3

    def __init__(
        self,
        database: SQLiteDatabase | Path | None = None,
        *,
        path: Path | None = None,
    ) -> None:
        if database is None and path is not None:
            database = path
        if isinstance(database, SQLiteDatabase):
            self._database = database
        else:
            self._database = sqlite_database(database or "api_test.db")
        self.path = self._database.path
        self.ensure_schema()

    @property
    def storage(self) -> SQLiteDatabase:
        return self._database

    def connect(self) -> SQLiteConnection:
        return self._database.open()

    def ensure_schema(self) -> None:
        with self._database.connection() as conn:
            self._create_schema(conn)
            _ensure_columns(
                conn,
                "http_tabs",
                {
                    "body_mode": "TEXT NOT NULL DEFAULT 'none'",
                    "path_params_text": "TEXT NOT NULL DEFAULT ''",
                    "node_id": "TEXT NOT NULL DEFAULT ''",
                    "mock_mode": "INTEGER NOT NULL DEFAULT 0",
                },
            )
            _ensure_columns(
                conn,
                "debug_cases",
                {
                    "body_mode": "TEXT NOT NULL DEFAULT 'none'",
                    "path_params_text": "TEXT NOT NULL DEFAULT ''",
                    "mock_mode": "INTEGER NOT NULL DEFAULT 0",
                },
            )
            self._migrate_legacy_state(conn)
            self._migrate_tab_bodies(conn, "http_tabs")
            self._migrate_tab_bodies(conn, "debug_cases")
            self._import_legacy_project_database(conn)
            self._recover_collection_tree(conn)
            self._seed_default_environment(conn)
            conn.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")

    def _migrate_legacy_state(self, conn: SQLiteConnection) -> None:
        self._import_collection_tree_from(conn, conn)
        self._import_environments_from(conn, conn)

    def _import_legacy_project_database(self, conn: SQLiteConnection) -> None:
        legacy_path = self._legacy_project_db_path()
        try:
            if not legacy_path.exists() or legacy_path.resolve() == self.path.resolve():
                return
        except OSError:
            return
        try:
            with sqlite3.connect(str(legacy_path)) as legacy_conn:
                legacy_conn.row_factory = sqlite3.Row
                self._import_collection_tree_from(conn, legacy_conn)
                self._import_environments_from(conn, legacy_conn)
                self._import_tabs_from(conn, legacy_conn)
                self._import_history_from(conn, legacy_conn)
                self._import_debug_cases_from(conn, legacy_conn)
        except sqlite3.DatabaseError:
            return

    def _import_collection_tree_from(
        self,
        target_conn: SQLiteConnection,
        source_conn: SQLiteConnection,
    ) -> None:
        if _table_row_count(target_conn, "api_collection_nodes") > 0:
            return
        if _table_exists(source_conn, "api_collection_nodes"):
            rows = source_conn.execute(
                """
                SELECT id, parent_id, kind, name, method, url, request_json, sort_order, expanded, created_at, updated_at
                FROM api_collection_nodes
                ORDER BY parent_id, sort_order, created_at
                """
            ).fetchall()
            if rows:
                target_conn.executemany(
                    """
                    INSERT INTO api_collection_nodes (
                        id, parent_id, kind, name, method, url, request_json, sort_order, expanded, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [tuple(row) for row in rows],
                )
                return
        tree = _legacy_collection_tree(source_conn)
        if tree:
            _insert_collection_tree(target_conn, tree)

    def _import_environments_from(
        self,
        target_conn: SQLiteConnection,
        source_conn: SQLiteConnection,
    ) -> None:
        if _table_row_count(target_conn, "api_environments") > 0:
            return
        if _table_exists(source_conn, "api_environments"):
            env_rows = source_conn.execute(
                """
                SELECT id, name, base_url, sort_order, created_at, updated_at
                FROM api_environments
                ORDER BY sort_order, created_at
                """
            ).fetchall()
            if env_rows:
                variable_rows = source_conn.execute(
                    """
                    SELECT id, environment_id, enabled, var_key, var_value, sort_order, created_at, updated_at
                    FROM api_environment_variables
                    ORDER BY environment_id, sort_order, created_at
                    """
                ).fetchall()
                header_rows = source_conn.execute(
                    """
                    SELECT id, environment_id, enabled, header_key, header_value, sort_order, created_at, updated_at
                    FROM api_environment_headers
                    ORDER BY environment_id, sort_order, created_at
                    """
                ).fetchall()
                target_conn.executemany(
                    """
                    INSERT INTO api_environments (id, name, base_url, sort_order, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [tuple(row) for row in env_rows],
                )
                if variable_rows:
                    target_conn.executemany(
                        """
                        INSERT INTO api_environment_variables (
                            id, environment_id, enabled, var_key, var_value, sort_order, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [tuple(row) for row in variable_rows],
                    )
                if header_rows:
                    target_conn.executemany(
                        """
                        INSERT INTO api_environment_headers (
                            id, environment_id, enabled, header_key, header_value, sort_order, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [tuple(row) for row in header_rows],
                    )
                return
        environments = _legacy_environments(source_conn)
        if not environments:
            return
        now = int(time.time() * 1000)
        for env_index, env in enumerate(environments):
            env_id = str(env.get("id") or uuid4())
            target_conn.execute(
                """
                INSERT INTO api_environments (id, name, base_url, sort_order, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    env_id,
                    str(env.get("name") or f"环境 {env_index + 1}"),
                    str(env.get("baseUrl") or ""),
                    env_index,
                    now,
                    now,
                ),
            )
            variables = env.get("variables") or []
            headers = env.get("headers") or []
            if variables:
                target_conn.executemany(
                    """
                    INSERT INTO api_environment_variables (
                        id, environment_id, enabled, var_key, var_value, sort_order, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            str(uuid4()),
                            env_id,
                            1 if row.get("enabled") is not False else 0,
                            str(row.get("key") or ""),
                            str(row.get("value") or ""),
                            row_index,
                            now,
                            now,
                        )
                        for row_index, row in enumerate(variables)
                        if isinstance(row, dict)
                    ],
                )
            if headers:
                target_conn.executemany(
                    """
                    INSERT INTO api_environment_headers (
                        id, environment_id, enabled, header_key, header_value, sort_order, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            str(uuid4()),
                            env_id,
                            1 if row.get("enabled") is not False else 0,
                            str(row.get("key") or ""),
                            str(row.get("value") or ""),
                            row_index,
                            now,
                            now,
                        )
                        for row_index, row in enumerate(headers)
                        if isinstance(row, dict)
                    ],
                )

    def _import_tabs_from(
        self,
        target_conn: SQLiteConnection,
        source_conn: SQLiteConnection,
    ) -> None:
        if _table_row_count(target_conn, "http_tabs") > 0 or not _table_exists(source_conn, "http_tabs"):
            return
        rows = source_conn.execute("SELECT * FROM http_tabs ORDER BY updated_at DESC").fetchall()
        if not rows:
            return
        for row in rows:
            body_mode, body_text = _normalize_body_storage(
                _row_value(row, "body_text", ""),
                _row_value(row, "body_mode", ""),
            )
            target_conn.execute(
                """
                INSERT INTO http_tabs (
                    id, name, method, url, request_mode, body_mode, auth_type, auth_value,
                    headers_text, cookies_text, body_text, params_text, path_params_text,
                    env_base_url, pre_ops_text, post_ops_text, node_id, mock_mode, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(_row_value(row, "id", uuid4().hex)),
                    str(_row_value(row, "name", "新接口")),
                    _normalize_method(_row_value(row, "method", "GET")),
                    str(_row_value(row, "url", "/")),
                    str(_row_value(row, "request_mode", "http")),
                    body_mode,
                    str(_row_value(row, "auth_type", "none")),
                    str(_row_value(row, "auth_value", "")),
                    str(_row_value(row, "headers_text", "")),
                    str(_row_value(row, "cookies_text", "")),
                    body_text,
                    str(_row_value(row, "params_text", "")),
                    str(_row_value(row, "path_params_text", "")),
                    str(_row_value(row, "env_base_url", "")),
                    str(_row_value(row, "pre_ops_text", "")),
                    str(_row_value(row, "post_ops_text", "")),
                    str(_row_value(row, "node_id", "")),
                    1 if bool(_row_value(row, "mock_mode", 0)) else 0,
                    int(_row_value(row, "updated_at", int(time.time() * 1000))),
                ),
            )

    def _import_history_from(
        self,
        target_conn: SQLiteConnection,
        source_conn: SQLiteConnection,
    ) -> None:
        if _table_row_count(target_conn, "http_history") > 0 or not _table_exists(source_conn, "http_history"):
            return
        rows = source_conn.execute(
            """
            SELECT tab_id, method, url, status, title, response, created_at
            FROM http_history
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()
        if not rows:
            return
        target_conn.executemany(
            """
            INSERT INTO http_history (tab_id, method, url, status, title, response, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [tuple(row) for row in rows],
        )

    def _import_debug_cases_from(
        self,
        target_conn: SQLiteConnection,
        source_conn: SQLiteConnection,
    ) -> None:
        if _table_row_count(target_conn, "debug_cases") > 0 or not _table_exists(source_conn, "debug_cases"):
            return
        rows = source_conn.execute("SELECT * FROM debug_cases ORDER BY updated_at DESC").fetchall()
        if not rows:
            return
        for row in rows:
            body_mode, body_text = _normalize_body_storage(
                _row_value(row, "body_text", ""),
                _row_value(row, "body_mode", ""),
            )
            target_conn.execute(
                """
                INSERT INTO debug_cases (
                    id, endpoint_key, name, method, url, request_mode, body_mode, auth_type, auth_value,
                    headers_text, cookies_text, body_text, params_text, path_params_text, env_base_url,
                    pre_ops_text, post_ops_text, mock_mode, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(_row_value(row, "id", f"case_{uuid4().hex}")),
                    str(_row_value(row, "endpoint_key", "")),
                    str(_row_value(row, "name", "用例")),
                    _normalize_method(_row_value(row, "method", "GET")),
                    str(_row_value(row, "url", "/")),
                    str(_row_value(row, "request_mode", "http")),
                    body_mode,
                    str(_row_value(row, "auth_type", "none")),
                    str(_row_value(row, "auth_value", "")),
                    str(_row_value(row, "headers_text", "")),
                    str(_row_value(row, "cookies_text", "")),
                    body_text,
                    str(_row_value(row, "params_text", "")),
                    str(_row_value(row, "path_params_text", "")),
                    str(_row_value(row, "env_base_url", "")),
                    str(_row_value(row, "pre_ops_text", "")),
                    str(_row_value(row, "post_ops_text", "")),
                    1 if bool(_row_value(row, "mock_mode", 0)) else 0,
                    int(_row_value(row, "updated_at", int(time.time() * 1000))),
                ),
            )

    def _migrate_tab_bodies(self, conn: SQLiteConnection, table_name: str) -> None:
        if not _table_exists(conn, table_name):
            return
        rows = conn.execute(f"SELECT id, body_mode, body_text FROM {table_name}").fetchall()
        for row_id, body_mode, body_text in rows:
            next_mode, next_body_text = _normalize_body_storage(body_text, body_mode)
            if next_mode == str(body_mode or "") and next_body_text == str(body_text or ""):
                continue
            conn.execute(
                f"UPDATE {table_name} SET body_mode = ?, body_text = ? WHERE id = ?",
                (next_mode, next_body_text, row_id),
            )

    def _recover_collection_tree(self, conn: SQLiteConnection) -> None:
        if _table_row_count(conn, "api_collection_nodes") > 0:
            return
        recovered: list[dict] = []
        seen: set[tuple[str, str]] = set()
        tab_rows = conn.execute(
            """
            SELECT name, method, url
            FROM http_tabs
            ORDER BY updated_at DESC
            """
        ).fetchall()
        for name, method, url in tab_rows:
            key = (_normalize_method(method or "GET"), str(url or "/"))
            if key in seen:
                continue
            seen.add(key)
            recovered.append(
                {
                    "kind": "endpoint",
                    "name": str(name or f"{key[0]} {key[1]}"),
                    "method": key[0],
                    "path": key[1],
                }
            )
        if not recovered:
            history_rows = conn.execute(
                """
                SELECT method, url, MAX(created_at) AS last_seen
                FROM http_history
                GROUP BY method, url
                ORDER BY last_seen DESC
                LIMIT 200
                """
            ).fetchall()
            for method, url, _ in history_rows:
                key = (_normalize_method(method or "GET"), str(url or "/"))
                if key in seen:
                    continue
                seen.add(key)
                recovered.append(
                    {
                        "kind": "endpoint",
                        "name": f"{key[0]} {key[1]}",
                        "method": key[0],
                        "path": key[1],
                    }
                )
        if not recovered:
            return
        _insert_collection_tree(
            conn,
            [
                {
                    "kind": "folder",
                    "name": "恢复接口",
                    "expanded": True,
                    "children": recovered,
                }
            ],
        )

    def _seed_default_environment(self, conn: SQLiteConnection) -> None:
        row = conn.execute("SELECT id FROM api_environments LIMIT 1").fetchone()
        if row is not None:
            return
        now = int(time.time() * 1000)
        conn.execute(
            """
            INSERT INTO api_environments (id, name, base_url, sort_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (str(uuid4()), "默认环境", "http://127.0.0.1:8000", 0, now, now),
        )

    @staticmethod
    def _create_schema(conn: SQLiteConnection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS http_tabs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                method TEXT NOT NULL,
                url TEXT NOT NULL,
                request_mode TEXT NOT NULL,
                body_mode TEXT NOT NULL DEFAULT 'none',
                auth_type TEXT NOT NULL,
                auth_value TEXT NOT NULL,
                headers_text TEXT NOT NULL,
                cookies_text TEXT NOT NULL DEFAULT '',
                body_text TEXT NOT NULL,
                params_text TEXT NOT NULL,
                path_params_text TEXT NOT NULL DEFAULT '',
                env_base_url TEXT NOT NULL,
                pre_ops_text TEXT NOT NULL DEFAULT '',
                post_ops_text TEXT NOT NULL DEFAULT '',
                node_id TEXT NOT NULL DEFAULT '',
                mock_mode INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS http_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tab_id TEXT NOT NULL,
                method TEXT NOT NULL,
                url TEXT NOT NULL,
                status INTEGER NOT NULL,
                title TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS api_collection_nodes (
                id TEXT PRIMARY KEY,
                parent_id TEXT NOT NULL DEFAULT '',
                kind TEXT NOT NULL CHECK(kind IN ('folder', 'endpoint', 'case')),
                name TEXT NOT NULL,
                method TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL DEFAULT '',
                request_json TEXT NOT NULL DEFAULT '{}',
                sort_order INTEGER NOT NULL,
                expanded INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_api_collection_nodes_parent_order
            ON api_collection_nodes(parent_id, sort_order);

            CREATE INDEX IF NOT EXISTS idx_api_collection_nodes_kind
            ON api_collection_nodes(kind);

            CREATE TABLE IF NOT EXISTS api_environments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                base_url TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS api_environment_variables (
                id TEXT PRIMARY KEY,
                environment_id TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                var_key TEXT NOT NULL DEFAULT '',
                var_value TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(environment_id) REFERENCES api_environments(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS api_environment_headers (
                id TEXT PRIMARY KEY,
                environment_id TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                header_key TEXT NOT NULL DEFAULT '',
                header_value TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(environment_id) REFERENCES api_environments(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_api_environments_order
            ON api_environments(sort_order);

            CREATE INDEX IF NOT EXISTS idx_api_environment_variables_env_order
            ON api_environment_variables(environment_id, sort_order);

            CREATE INDEX IF NOT EXISTS idx_api_environment_headers_env_order
            ON api_environment_headers(environment_id, sort_order);

            CREATE TABLE IF NOT EXISTS debug_cases (
                id TEXT PRIMARY KEY,
                endpoint_key TEXT NOT NULL,
                name TEXT NOT NULL,
                method TEXT NOT NULL,
                url TEXT NOT NULL,
                request_mode TEXT NOT NULL,
                body_mode TEXT NOT NULL DEFAULT 'none',
                auth_type TEXT NOT NULL,
                auth_value TEXT NOT NULL,
                headers_text TEXT NOT NULL,
                cookies_text TEXT NOT NULL DEFAULT '',
                body_text TEXT NOT NULL,
                params_text TEXT NOT NULL,
                path_params_text TEXT NOT NULL DEFAULT '',
                env_base_url TEXT NOT NULL,
                pre_ops_text TEXT NOT NULL DEFAULT '',
                post_ops_text TEXT NOT NULL DEFAULT '',
                mock_mode INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ws_sessions (
                tab_id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                status TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ws_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tab_id TEXT NOT NULL,
                direction TEXT NOT NULL,
                msg_type TEXT NOT NULL,
                encoding TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS api_variables (
                scope TEXT NOT NULL,
                env_name TEXT NOT NULL DEFAULT '',
                var_key TEXT NOT NULL,
                var_value TEXT NOT NULL DEFAULT '',
                updated_at INTEGER NOT NULL,
                PRIMARY KEY(scope, env_name, var_key)
            );
            """
        )

    @staticmethod
    def _legacy_project_db_path() -> Path:
        return Path(__file__).resolve().parents[3] / "data" / "api_test.db"


def _table_exists(conn: SQLiteConnection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(conn: SQLiteConnection, table_name: str) -> set[str]:
    if not _table_exists(conn, table_name):
        return set()
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def _ensure_columns(conn: SQLiteConnection, table_name: str, columns: dict[str, str]) -> None:
    existing = _table_columns(conn, table_name)
    if not existing:
        return
    for name, ddl in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {name} {ddl}")


def _table_row_count(conn: SQLiteConnection, table_name: str) -> int:
    if not _table_exists(conn, table_name):
        return 0
    row = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
    return int(row[0] or 0) if row is not None else 0


def _row_value(row, key: str, default):
    try:
        value = row[key]
    except Exception:
        return default
    return default if value is None else value


def _normalize_method(value: str) -> str:
    method = str(value or "GET").upper()
    return "DELETE" if method == "DEL" else method


def _normalize_body_storage(body_text: str, body_mode: str) -> tuple[str, str]:
    text = str(body_text or "")
    mode = str(body_mode or "").strip()
    stripped = text.strip()
    try:
        loaded = json.loads(text or "{}")
    except Exception:
        loaded = None
    if isinstance(loaded, dict) and any(key in _BODY_MODES for key in loaded):
        if mode in _BODY_MODES:
            return mode, json.dumps(loaded, ensure_ascii=False)
        for candidate in _BODY_MODES:
            if candidate in loaded:
                return candidate, json.dumps(loaded, ensure_ascii=False)
        return "none", json.dumps(loaded, ensure_ascii=False)
    if not stripped:
        return "none", "{}"
    next_mode = mode if mode in _BODY_MODES and mode != "none" else _infer_body_mode(stripped)
    return next_mode, json.dumps({next_mode: text}, ensure_ascii=False)


def _infer_body_mode(text: str) -> str:
    if _looks_like_form_urlencoded(text):
        return "x-www-form-urlencoded"
    if _looks_like_json(text):
        return "JSON"
    if text.startswith("<") and text.endswith(">"):
        return "XML"
    return "Text"


def _looks_like_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except Exception:
        return False


def _looks_like_form_urlencoded(text: str) -> bool:
    if "=" not in text or "\n" in text or "\r" in text:
        return False
    if text.startswith("{") or text.startswith("[") or text.startswith("<"):
        return False
    parts = [part for part in text.split("&") if part]
    return bool(parts) and all("=" in part for part in parts)


def _legacy_environments(conn: SQLiteConnection) -> list[dict]:
    if not _table_exists(conn, "app_state"):
        return []
    row = conn.execute(
        "SELECT state_value FROM app_state WHERE state_key = 'environments'"
    ).fetchone()
    if row is None:
        return []
    try:
        loaded = json.loads(row[0] or "[]")
    except Exception:
        return []
    if not isinstance(loaded, list):
        return []
    environments: list[dict] = []
    for index, env in enumerate(loaded):
        if not isinstance(env, dict):
            continue
        environments.append(
            {
                "id": str(env.get("id") or uuid4()),
                "name": str(env.get("name") or f"环境 {index + 1}"),
                "baseUrl": str(env.get("baseUrl") or ""),
                "variables": env.get("variables") if isinstance(env.get("variables"), list) else [],
                "headers": env.get("headers") if isinstance(env.get("headers"), list) else [],
            }
        )
    return environments


def _legacy_collection_tree(conn: SQLiteConnection) -> list[dict]:
    if not _table_exists(conn, "app_state"):
        return []
    row = conn.execute(
        "SELECT state_value FROM app_state WHERE state_key = 'collection_tree'"
    ).fetchone()
    if row is None:
        return []
    try:
        loaded = json.loads(row[0] or "[]")
    except Exception:
        return []
    if not isinstance(loaded, list):
        return []
    if (
        len(loaded) == 1
        and isinstance(loaded[0], dict)
        and loaded[0].get("name") == "默认模块"
        and isinstance(loaded[0].get("children"), list)
        and len(loaded[0]["children"]) == 1
        and isinstance(loaded[0]["children"][0], dict)
        and loaded[0]["children"][0].get("name") == "接口"
    ):
        children = loaded[0]["children"][0].get("children")
        if isinstance(children, list):
            loaded = children
    return loaded


def _insert_collection_tree(conn: SQLiteConnection, tree: list[dict]) -> None:
    rows: list[tuple] = []
    now = int(time.time() * 1000)

    def visit(nodes: list[dict], parent_id: str) -> None:
        for index, node in enumerate(nodes or []):
            if not isinstance(node, dict):
                continue
            kind = _collection_kind(node)
            if kind not in {"folder", "endpoint", "case"}:
                continue
            node_id = str(node.get("id") or uuid4())
            name = str(node.get("name") or ("未命名分组" if kind == "folder" else "新接口"))
            method = _normalize_method(node.get("method") or "GET") if kind == "endpoint" else ""
            url = str(node.get("path") or node.get("url") or ("/" if kind == "endpoint" else ""))
            snapshot = _case_snapshot(node, name, method or "GET", url or "/") if kind == "case" else {}
            rows.append(
                (
                    node_id,
                    parent_id,
                    kind,
                    name,
                    method,
                    url,
                    json.dumps(snapshot, ensure_ascii=False),
                    index,
                    1 if kind in {"folder", "endpoint"} and node.get("expanded") is not False else 0,
                    int(node.get("createdAt") or now),
                    int(node.get("updatedAt") or now),
                )
            )
            children = node.get("children")
            if kind in {"folder", "endpoint"} and isinstance(children, list):
                visit(children, node_id)

    visit(tree, "")
    if not rows:
        return
    conn.executemany(
        """
        INSERT INTO api_collection_nodes (
            id, parent_id, kind, name, method, url, request_json, sort_order, expanded, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _collection_kind(node: dict) -> str:
    kind = str(node.get("kind") or node.get("type") or "").strip().lower()
    if kind in {"folder", "endpoint", "case"}:
        return kind
    method = _normalize_method(str(node.get("method") or ""))
    if method == "CASE":
        return "case"
    if node.get("path") or node.get("url") or node.get("method"):
        return "endpoint"
    return "folder"


def _case_snapshot(node: dict, name: str, method: str, url: str) -> dict:
    snapshot = node.get("requestSnapshot")
    if isinstance(snapshot, dict):
        return snapshot
    return {
        "name": name,
        "method": method,
        "url": url,
    }

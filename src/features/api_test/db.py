from __future__ import annotations

import time
from uuid import uuid4

from app.storage import SQLiteConnection, SQLiteDatabase


class ApiDatabase:
    SCHEMA_VERSION = 4

    def __init__(
        self,
        database: SQLiteDatabase,
    ) -> None:
        self._database = database
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
            self._migrate(conn)
            self._seed_default_environment(conn)
            conn.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")

    @staticmethod
    def _migrate(conn: SQLiteConnection) -> None:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(http_tabs)").fetchall()}
        if "active_request_tab" not in cols:
            conn.execute("ALTER TABLE http_tabs ADD COLUMN active_request_tab INTEGER NOT NULL DEFAULT 0")

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
                active_request_tab INTEGER NOT NULL DEFAULT 0,
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


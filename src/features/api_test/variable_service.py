from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.storage import SQLiteDatabase, sqlite_database


class VariableService:
    """Project-scoped variables with non-team precedence."""

    _pattern = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")

    def __init__(self, database: SQLiteDatabase | str | Path) -> None:
        self._database = database if isinstance(database, SQLiteDatabase) else sqlite_database(database)
        self._db_path = self._database.path
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self._database.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_variables (
                    scope TEXT NOT NULL,
                    env_name TEXT NOT NULL DEFAULT '',
                    var_key TEXT NOT NULL,
                    var_value TEXT NOT NULL DEFAULT '',
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY(scope, env_name, var_key)
                )
                """
            )

    def set_variable(self, scope: str, key: str, value: str, env_name: str = "", updated_at: int = 0) -> None:
        if not key.strip():
            return
        with self._database.connection() as conn:
            conn.execute(
                """
                INSERT INTO api_variables (scope, env_name, var_key, var_value, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(scope, env_name, var_key) DO UPDATE SET
                    var_value=excluded.var_value,
                    updated_at=excluded.updated_at
                """,
                (scope, env_name, key.strip(), value, updated_at),
            )

    def resolve_text(
        self,
        text: str,
        *,
        env_name: str = "",
        temporary: dict[str, Any] | None = None,
        module_vars: dict[str, Any] | None = None,
        env_vars: dict[str, Any] | None = None,
    ) -> str:
        if not text:
            return text
        temporary = temporary or {}
        module_vars = module_vars or {}
        env_vars = env_vars or {}
        globals_map = self._load_scope_variables("global")
        env_store = self._load_scope_variables("environment", env_name=env_name)
        module_store = self._load_scope_variables("module")

        def replace(match: re.Match[str]) -> str:
            key = match.group(1).strip()
            if key in temporary:
                return str(temporary[key])
            if key in env_vars:
                return str(env_vars[key])
            if key in env_store:
                return str(env_store[key])
            if key in module_vars:
                return str(module_vars[key])
            if key in module_store:
                return str(module_store[key])
            if key in globals_map:
                return str(globals_map[key])
            return match.group(0)

        return self._pattern.sub(replace, text)

    def _load_scope_variables(self, scope: str, env_name: str = "") -> dict[str, str]:
        with self._database.connection() as conn:
            rows = conn.execute(
                """
                SELECT var_key, var_value
                FROM api_variables
                WHERE scope = ? AND env_name = ?
                """,
                (scope, env_name),
            ).fetchall()
        return {k: v for k, v in rows}

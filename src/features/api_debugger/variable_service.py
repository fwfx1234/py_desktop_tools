from __future__ import annotations

from base64 import b64encode
from datetime import datetime, timezone
import random
import re
import string
import time
from typing import Any
from uuid import uuid4

from app.storage import SQLiteDatabase


class VariableService:
    """Project-scoped variables with non-team precedence."""

    _pattern = re.compile(r"\{\{\s*([a-zA-Z0-9_.\-$]+)\s*\}\}")

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database
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
            magic_value = self._magic_value(key)
            if magic_value is not None:
                return magic_value
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

    def resolve_mapping(
        self,
        values: dict[str, str],
        *,
        env_name: str = "",
        temporary: dict[str, Any] | None = None,
        module_vars: dict[str, Any] | None = None,
        env_vars: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        return {
            self.resolve_text(str(k), env_name=env_name, temporary=temporary, module_vars=module_vars, env_vars=env_vars):
            self.resolve_text(str(v), env_name=env_name, temporary=temporary, module_vars=module_vars, env_vars=env_vars)
            for k, v in values.items()
        }

    @staticmethod
    def _magic_value(key: str) -> str | None:
        now = datetime.now(timezone.utc)
        if key == "$timestamp":
            return str(int(time.time()))
        if key == "$timestamp_ms":
            return str(int(time.time() * 1000))
        if key == "$iso_datetime":
            return now.isoformat(timespec="seconds").replace("+00:00", "Z")
        if key == "$date":
            return now.date().isoformat()
        if key == "$uuid":
            return str(uuid4())
        if key == "$uuid_simple":
            return uuid4().hex
        if key == "$time":
            return now.strftime("%H:%M:%S")
        if key == "$datetime":
            return now.strftime("%Y-%m-%d %H:%M:%S")
        if key == "$year":
            return now.strftime("%Y")
        if key == "$month":
            return now.strftime("%m")
        if key == "$day":
            return now.strftime("%d")
        if key == "$random_int":
            return str(random.randint(0, 1000000))
        if key == "$random_4":
            return str(random.randint(1000, 9999))
        if key == "$random_6":
            return str(random.randint(100000, 999999))
        if key == "$random_8":
            return str(random.randint(10000000, 99999999))
        if key == "$random_bool":
            return "true" if random.choice((True, False)) else "false"
        if key == "$random_string":
            return "".join(random.choices(string.ascii_letters + string.digits, k=12))
        if key == "$random_hex":
            return "".join(random.choices("0123456789abcdef", k=16))
        if key == "$random_email":
            local = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
            return f"{local}@example.com"
        if key == "$base64_random":
            raw = "".join(random.choices(string.ascii_letters + string.digits, k=18))
            return b64encode(raw.encode("utf-8")).decode("ascii")
        return None

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

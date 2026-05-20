from __future__ import annotations

import time
from uuid import uuid4

from app.storage import SQLiteDatabase


class EnvironmentRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database
        self._db_path = self._database.path

    def list_environments(self) -> list[dict]:
        with self._database.connection() as conn:
            env_rows = conn.execute(
                """
                SELECT id, name, base_url
                FROM api_environments
                ORDER BY sort_order, created_at
                """
            ).fetchall()
            variable_rows = conn.execute(
                """
                SELECT environment_id, enabled, var_key, var_value
                FROM api_environment_variables
                ORDER BY environment_id, sort_order, created_at
                """
            ).fetchall()
            header_rows = conn.execute(
                """
                SELECT environment_id, enabled, header_key, header_value
                FROM api_environment_headers
                ORDER BY environment_id, sort_order, created_at
                """
            ).fetchall()

        variables_by_env: dict[str, list[dict]] = {}
        for env_id, enabled, key, value in variable_rows:
            variables_by_env.setdefault(env_id, []).append(
                {"enabled": bool(enabled), "key": key or "", "value": value or ""}
            )

        headers_by_env: dict[str, list[dict]] = {}
        for env_id, enabled, key, value in header_rows:
            headers_by_env.setdefault(env_id, []).append(
                {"enabled": bool(enabled), "key": key or "", "value": value or ""}
            )

        environments = [
            {
                "id": env_id,
                "name": name,
                "baseUrl": base_url,
                "variables": variables_by_env.get(env_id, []),
                "headers": headers_by_env.get(env_id, []),
            }
            for env_id, name, base_url in env_rows
        ]
        return environments or [_default_environment()]

    def save_environments(self, environments: list[dict]) -> None:
        envs = _normalize_environments(environments)
        now = int(time.time() * 1000)
        with self._database.connection() as conn:
            conn.execute("DELETE FROM api_environments")
            for env_index, env in enumerate(envs):
                env_id = str(env.get("id") or uuid4())
                conn.execute(
                    """
                    INSERT INTO api_environments (id, name, base_url, sort_order, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    env_id,
                    str(env.get("name") or ""),
                    str(env.get("baseUrl") or ""),
                    env_index,
                    now,
                        now,
                    ),
                )
                conn.executemany(
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
                        for row_index, row in enumerate(env.get("variables") or [])
                    ],
                )
                conn.executemany(
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
                        for row_index, row in enumerate(env.get("headers") or [])
                    ],
                )

def _normalize_environments(environments: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for index, env in enumerate(environments or []):
        if not isinstance(env, dict):
            continue
        variables = _normalize_rows(env.get("variables") or [])
        headers = _normalize_rows(env.get("headers") or [])
        normalized.append(
            {
                "id": str(env.get("id") or uuid4()),
                "name": str(env.get("name") or "").strip(),
                "baseUrl": str(env.get("baseUrl") or "").strip(),
                "variables": variables,
                "headers": headers,
            }
        )
    return normalized or [_default_environment()]


def _normalize_rows(rows: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("key") or "").strip()
        value = str(row.get("value") or "")
        if not key and not value:
            continue
        normalized.append(
            {
                "enabled": row.get("enabled") is not False,
                "key": key,
                "value": value,
            }
        )
    return normalized


def _default_environment() -> dict:
    return {
        "id": str(uuid4()),
        "name": "默认环境",
        "baseUrl": "http://127.0.0.1:8000",
        "variables": [],
        "headers": [],
    }

from __future__ import annotations

import time
from typing import Any, Callable

from app.storage import SQLiteDatabase


class DebugCaseService:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database
        self._db_path = self._database.path
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self._database.connection() as conn:
            conn.execute(
                """
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
                )
                """
            )

    def save_case(self, *, case_id: str, endpoint_key: str, payload: dict[str, Any]) -> None:
        now = int(time.time() * 1000)
        with self._database.connection() as conn:
            conn.execute(
                """
                INSERT INTO debug_cases (
                    id, endpoint_key, name, method, url, request_mode, body_mode, auth_type, auth_value,
                    headers_text, cookies_text, body_text, params_text, path_params_text, env_base_url,
                    pre_ops_text, post_ops_text, mock_mode, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    endpoint_key=excluded.endpoint_key,
                    name=excluded.name,
                    method=excluded.method,
                    url=excluded.url,
                    request_mode=excluded.request_mode,
                    body_mode=excluded.body_mode,
                    auth_type=excluded.auth_type,
                    auth_value=excluded.auth_value,
                    headers_text=excluded.headers_text,
                    cookies_text=excluded.cookies_text,
                    body_text=excluded.body_text,
                    params_text=excluded.params_text,
                    path_params_text=excluded.path_params_text,
                    env_base_url=excluded.env_base_url,
                    pre_ops_text=excluded.pre_ops_text,
                    post_ops_text=excluded.post_ops_text,
                    mock_mode=excluded.mock_mode,
                    updated_at=excluded.updated_at
                """,
                (
                    case_id,
                    endpoint_key,
                    payload.get("name", "用例"),
                    payload.get("method", "GET"),
                    payload.get("url", "/"),
                    payload.get("requestMode", "http"),
                    payload.get("bodyMode", "none"),
                    payload.get("authType", "none"),
                    payload.get("authValue", ""),
                    payload.get("headersText", ""),
                    payload.get("cookiesText", ""),
                    payload.get("bodyText", ""),
                    payload.get("paramsText", ""),
                    payload.get("pathParamsText", ""),
                    payload.get("envBaseUrl", ""),
                    payload.get("preOpsText", ""),
                    payload.get("postOpsText", ""),
                    1 if payload.get("mockMode") else 0,
                    now,
                ),
            )

    def list_cases(self, endpoint_key: str) -> list[dict[str, Any]]:
        with self._database.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, name, method, url, request_mode, body_mode, auth_type, auth_value,
                       headers_text, cookies_text, body_text, params_text, path_params_text,
                       env_base_url, pre_ops_text, post_ops_text, mock_mode, updated_at
                FROM debug_cases
                WHERE endpoint_key = ?
                ORDER BY updated_at DESC
                """,
                (endpoint_key,),
            ).fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "method": row[2],
                "url": row[3],
                "requestMode": row[4],
                "bodyMode": row[5],
                "authType": row[6],
                "authValue": row[7],
                "headersText": row[8],
                "cookiesText": row[9],
                "bodyText": row[10],
                "paramsText": row[11],
                "pathParamsText": row[12],
                "envBaseUrl": row[13],
                "preOpsText": row[14],
                "postOpsText": row[15],
                "mockMode": bool(row[16]),
                "updatedAt": row[17],
            }
            for row in rows
        ]

    def run_batch(
        self,
        endpoint_key: str,
        selected_case_ids: list[str],
        sender: Callable[[dict[str, Any]], tuple[str, str, dict]],
    ) -> list[dict[str, str]]:
        if not selected_case_ids:
            return []
        all_cases = {c["id"]: c for c in self.list_cases(endpoint_key)}
        results: list[dict[str, str]] = []
        for cid in selected_case_ids:
            case = all_cases.get(cid)
            if case is None:
                continue
            result = sender(case)
            title, body = result[0], result[1]
            results.append({"id": cid, "name": case["name"], "title": title, "body": body})
        return results

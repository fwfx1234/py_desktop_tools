from __future__ import annotations

import time

from app.storage import SQLiteDatabase


class TabRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database
        self._db_path = self._database.path

    def list_tabs(self) -> list[dict]:
        with self._database.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, name, method, url, request_mode, body_mode, auth_type, auth_value,
                       headers_text, cookies_text, body_text, params_text, path_params_text,
                       env_base_url, pre_ops_text, post_ops_text, node_id, mock_mode,
                       active_request_tab, updated_at
                FROM http_tabs
                ORDER BY updated_at DESC
                """
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
                "nodeId": row[16],
                "mockMode": bool(row[17]),
                "activeRequestTab": int(row[18] or 0),
                "updatedAt": row[19],
            }
            for row in rows
        ]

    def upsert_tab(
        self,
        tab_id: str,
        name: str,
        method: str,
        url: str,
        request_mode: str,
        body_mode: str,
        auth_type: str,
        auth_value: str,
        headers_text: str,
        cookies_text: str,
        body_text: str,
        params_text: str,
        path_params_text: str,
        env_base_url: str,
        pre_ops_text: str,
        post_ops_text: str,
        node_id: str,
        mock_mode: bool,
        active_request_tab: int = 0,
    ) -> None:
        now = int(time.time() * 1000)
        with self._database.connection() as conn:
            conn.execute(
                """
                INSERT INTO http_tabs (
                    id, name, method, url, request_mode, body_mode, auth_type, auth_value,
                    headers_text, cookies_text, body_text, params_text, path_params_text,
                    env_base_url, pre_ops_text, post_ops_text, node_id, mock_mode,
                    active_request_tab, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
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
                    node_id=excluded.node_id,
                    mock_mode=excluded.mock_mode,
                    active_request_tab=excluded.active_request_tab,
                    updated_at=excluded.updated_at
                """,
                (
                    tab_id,
                    name,
                    method,
                    url,
                    request_mode,
                    body_mode,
                    auth_type,
                    auth_value,
                    headers_text,
                    cookies_text,
                    body_text,
                    params_text,
                    path_params_text,
                    env_base_url,
                    pre_ops_text,
                    post_ops_text,
                    node_id,
                    1 if mock_mode else 0,
                    max(0, int(active_request_tab or 0)),
                    now,
                ),
            )

    def delete_tab(self, tab_id: str) -> None:
        with self._database.connection() as conn:
            conn.execute("DELETE FROM http_tabs WHERE id = ?", (tab_id,))

    def list_history(self, limit: int = 100) -> list[dict]:
        with self._database.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, tab_id, method, url, status, title, response, created_at
                FROM http_history
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
        return [
            {
                "id": row[0],
                "tabId": row[1],
                "method": row[2],
                "url": row[3],
                "status": row[4],
                "title": row[5],
                "response": row[6],
                "createdAt": row[7],
            }
            for row in rows
        ]

    def record_history(
        self,
        *,
        tab_id: str,
        method: str,
        url: str,
        status: int,
        title: str,
        response: str,
        created_at: int | None = None,
    ) -> None:
        created = created_at if created_at is not None else int(time.time() * 1000)
        with self._database.connection() as conn:
            conn.execute(
                """
                INSERT INTO http_history (tab_id, method, url, status, title, response, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (tab_id or "", method, url, status, title, response[:50000], created),
            )

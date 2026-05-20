from __future__ import annotations

import base64
from threading import RLock
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from app.storage import SQLiteDatabase

from .variable_service import VariableService

if TYPE_CHECKING:
    from websocket import WebSocket


class WebSocketSessionService:
    def __init__(
        self,
        database: SQLiteDatabase,
        variable_service: VariableService,
    ) -> None:
        self._database = database
        self._db_path = self._database.path
        self._variable_service = variable_service
        self._connections: dict[str, "WebSocket"] = {}
        self._session_contexts: dict[str, tuple[str, dict[str, str]]] = {}
        self._lock = RLock()
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        with self._database.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ws_sessions (
                    tab_id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ws_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tab_id TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    msg_type TEXT NOT NULL,
                    encoding TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )

    def connect(
        self,
        *,
        tab_id: str,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
        cookies: str,
        env_name: str,
        env_base_url: str = "",
        env_vars: dict[str, str] | None = None,
    ) -> str:
        from websocket import create_connection

        env_vars = env_vars or {}
        resolved_url = self._resolve_url(url, env_base_url)
        final_url = self._build_url(resolved_url, params, env_name=env_name, env_vars=env_vars)
        headers = self._variable_service.resolve_mapping(headers, env_name=env_name, env_vars=env_vars)
        header_lines = [
            f"{k}: {v}"
            for k, v in headers.items()
        ]
        if cookies.strip():
            header_lines.append(f"Cookie: {self._variable_service.resolve_text(cookies, env_name=env_name, env_vars=env_vars)}")
        ws = create_connection(final_url, header=header_lines or None, timeout=10)
        with self._lock:
            previous = self._connections.get(tab_id)
            self._connections[tab_id] = ws
            self._session_contexts[tab_id] = (env_name, dict(env_vars))
        if previous is not None:
            try:
                previous.close()
            except Exception:
                pass
        self._upsert_session(tab_id, final_url, "connected")
        self._append_message(tab_id, "system", "status", "text", f"connected to {final_url}")
        return final_url

    def disconnect(self, tab_id: str) -> None:
        with self._lock:
            ws = self._connections.pop(tab_id, None)
            self._session_contexts.pop(tab_id, None)
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass
        self._upsert_session(tab_id, self._session_url(tab_id), "disconnected")
        self._append_message(tab_id, "system", "status", "text", "disconnected")

    def disconnect_all(self) -> None:
        with self._lock:
            tab_ids = list(self._connections.keys())
        for tab_id in tab_ids:
            self.disconnect(tab_id)

    def is_connected(self, tab_id: str) -> bool:
        with self._lock:
            return tab_id in self._connections

    def send_message(
        self,
        *,
        tab_id: str,
        content: str,
        encoding: str,
        env_name: str = "",
        env_vars: dict[str, str] | None = None,
    ) -> str:
        with self._lock:
            ws = self._connections.get(tab_id)
            stored_context = self._session_contexts.get(tab_id)
        if ws is None:
            raise RuntimeError("WebSocket 未连接，请先连接。")
        if stored_context and not env_name and env_vars is None:
            env_name, env_vars = stored_context
        env_vars = env_vars or {}
        payload = self._variable_service.resolve_text(content or "", env_name=env_name, env_vars=env_vars)
        if encoding == "base64":
            ws.send(base64.b64decode(payload), opcode=0x2)
        elif encoding == "hex":
            ws.send(bytes.fromhex(payload), opcode=0x2)
        else:
            ws.send(payload)
        self._append_message(tab_id, "out", "message", encoding, payload)
        return payload

    def receive_once(self, tab_id: str) -> str:
        with self._lock:
            ws = self._connections.get(tab_id)
        if ws is None:
            raise RuntimeError("WebSocket 未连接，请先连接。")
        msg = ws.recv()
        text = msg.decode("utf-8", errors="replace") if isinstance(msg, (bytes, bytearray)) else str(msg)
        encoding = "hex" if isinstance(msg, (bytes, bytearray)) else "text"
        self._append_message(tab_id, "in", "message", encoding, text)
        return text

    def list_timeline(self, tab_id: str, limit: int = 200) -> list[dict[str, Any]]:
        with self._database.connection() as conn:
            rows = conn.execute(
                """
                SELECT direction, msg_type, encoding, content, created_at
                FROM ws_messages
                WHERE tab_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (tab_id, limit),
            ).fetchall()
        return [
            {
                "direction": row[0],
                "type": row[1],
                "encoding": row[2],
                "content": row[3],
                "createdAt": row[4],
            }
            for row in rows
        ]

    def _append_message(self, tab_id: str, direction: str, msg_type: str, encoding: str, content: str) -> None:
        now = int(time.time() * 1000)
        with self._database.connection() as conn:
            conn.execute(
                """
                INSERT INTO ws_messages (tab_id, direction, msg_type, encoding, content, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (tab_id, direction, msg_type, encoding, content, now),
            )

    def _upsert_session(self, tab_id: str, url: str, status: str) -> None:
        now = int(time.time() * 1000)
        with self._database.connection() as conn:
            conn.execute(
                """
                INSERT INTO ws_sessions (tab_id, url, status, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(tab_id) DO UPDATE SET
                    url=excluded.url,
                    status=excluded.status,
                    updated_at=excluded.updated_at
                """,
                (tab_id, url, status, now),
            )

    def _session_url(self, tab_id: str) -> str:
        with self._database.connection() as conn:
            row = conn.execute("SELECT url FROM ws_sessions WHERE tab_id = ?", (tab_id,)).fetchone()
        return row[0] if row else ""

    @staticmethod
    def _resolve_url(url: str, base_url: str) -> str:
        u = (url or "").strip()
        base = (base_url or "").strip().rstrip("/")
        if not u:
            return base
        if u.startswith("http://") or u.startswith("https://") or u.startswith("ws://") or u.startswith("wss://") or not base:
            return u
        if u.startswith("/"):
            return f"{base}{u}"
        return f"{base}/{u}"

    def _build_url(self, url: str, params: dict[str, str], *, env_name: str, env_vars: dict[str, str]) -> str:
        resolved = self._variable_service.resolve_text(url, env_name=env_name, env_vars=env_vars)
        parsed = urlparse(resolved)
        query = dict(parse_qsl(parsed.query))
        query.update(self._variable_service.resolve_mapping(params, env_name=env_name, env_vars=env_vars))
        return urlunparse(parsed._replace(query=urlencode(query)))

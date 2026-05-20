from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from threading import RLock

from app.storage import DatabaseDictStore, SQLiteDatabase, SQLiteRow, dict_store

from .models import ClipboardItemDraft, DEFAULT_CLIPBOARD_CONFIG


class ClipboardHistoryStore:
    def __init__(
        self,
        database: SQLiteDatabase,
        settings_store: DatabaseDictStore | None = None,
    ) -> None:
        self._database = database
        self._db_path = self._database.path
        self._image_dir = self._db_path.parent / "clipboard_assets" / "images"
        self._image_dir.mkdir(parents=True, exist_ok=True)
        self._settings = (
            settings_store
            if settings_store is not None
            else dict_store(
                "clipboard/settings",
                defaults=DEFAULT_CLIPBOARD_CONFIG,
            )
        )
        self._lock = RLock()
        self._ensure_schema()

    @property
    def image_dir(self) -> Path:
        return self._image_dir

    def capture_draft(self, draft: ClipboardItemDraft) -> bool:
        if draft.item_type == "text":
            return self.add_text(draft.content)
        if draft.item_type == "files":
            paths = draft.metadata.get("paths", [])
            if not isinstance(paths, list):
                return False
            return self.add_files([str(path) for path in paths])
        if draft.item_type == "image":
            return self.add_image_bytes(
                draft.image_bytes or b"",
                width=int(draft.metadata.get("width") or 0),
                height=int(draft.metadata.get("height") or 0),
            )
        return False

    def add_text(self, text: str) -> bool:
        if not self.should_capture("text", text, text):
            return False
        value = text.rstrip("\x00")
        preview = self._compact_preview(value)
        return self.add_item("text", value, preview)

    def add_image_bytes(self, image_bytes: bytes, *, width: int = 0, height: int = 0) -> bool:
        if not image_bytes or not self.get_config_value("capture_image"):
            return False
        file_name = f"{uuid.uuid4().hex}.png"
        image_path = self._image_dir / file_name
        image_path.write_bytes(image_bytes)
        metadata = {
            "width": width,
            "height": height,
            "path": str(image_path),
        }
        preview = f"{width} x {height} PNG".strip()
        return self.add_item("image", str(image_path), preview, metadata)

    def add_files(self, paths: list[str]) -> bool:
        clean_paths = [str(Path(path)) for path in paths if path]
        if not clean_paths:
            return False
        names = [Path(path).name or path for path in clean_paths]
        preview = ", ".join(names[:3])
        if len(names) > 3:
            preview += f" ... (+{len(names) - 3})"
        if not self.should_capture("files", json.dumps(clean_paths, ensure_ascii=False), preview):
            return False
        return self.add_item(
            "files",
            json.dumps(clean_paths, ensure_ascii=False),
            preview,
            {"count": len(clean_paths), "paths": clean_paths},
        )

    def add_item(
        self,
        item_type: str,
        content: str,
        preview: str,
        metadata: dict | None = None,
        *,
        pinned: bool = False,
    ) -> bool:
        if not content:
            return False
        with self._lock:
            with self._database.connection(row_factory=SQLiteRow) as conn:
                latest = conn.execute(
                    "SELECT item_type, content FROM clipboard_history ORDER BY id DESC LIMIT 1"
                ).fetchone()
                if latest and latest["item_type"] == item_type and latest["content"] == content:
                    return False
                existing = conn.execute(
                    """
                    SELECT pinned
                    FROM clipboard_history
                    WHERE item_type = ? AND content = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (item_type, content),
                ).fetchone()
                if existing is not None:
                    pinned = bool(existing["pinned"]) or pinned
                    conn.execute(
                        "DELETE FROM clipboard_history WHERE item_type = ? AND content = ?",
                        (item_type, content),
                    )
                created_at = datetime.now().strftime("%m-%d %H:%M:%S")
                metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
                conn.execute(
                    """
                    INSERT INTO clipboard_history
                        (item_type, content, preview, metadata, pinned, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item_type,
                        content,
                        preview,
                        metadata_json,
                        1 if pinned else 0,
                        created_at,
                    ),
                )
        return True

    def promote_item(self, item_id: int) -> bool:
        item = self.get_item(item_id)
        if item is None:
            return False
        item_type = str(item.get("itemType") or "text")
        content = str(item.get("content") or "")
        if not content:
            return False
        with self._lock:
            with self._database.connection(row_factory=SQLiteRow) as conn:
                latest = conn.execute(
                    """
                    SELECT id, item_type, content
                    FROM clipboard_history
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ).fetchone()
                if latest is not None and int(latest["id"]) == item_id:
                    return False
                if (
                    latest is not None
                    and latest["item_type"] == item_type
                    and latest["content"] == content
                ):
                    return False
                conn.execute(
                    "DELETE FROM clipboard_history WHERE item_type = ? AND content = ?",
                    (item_type, content),
                )
                conn.execute(
                    """
                    INSERT INTO clipboard_history
                        (item_type, content, preview, metadata, pinned, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item_type,
                        content,
                        str(item.get("preview") or ""),
                        json.dumps(item.get("metadata") or {}, ensure_ascii=False),
                        1 if item.get("pinned") else 0,
                        datetime.now().strftime("%m-%d %H:%M:%S"),
                    ),
                )
        return True

    def search(
        self,
        query: str,
        *,
        filter_type: str = "all",
        offset: int = 0,
        limit: int | None = None,
    ) -> list[dict]:
        q = query.strip()
        filter_value = str(filter_type or "all")
        conditions: list[str] = []
        params: list[object] = []
        if filter_value == "pinned":
            conditions.append("pinned = 1")
        elif filter_value in {"text", "image", "files"}:
            conditions.append("item_type = ?")
            params.append(filter_value)
        if q:
            like = f"%{q}%"
            conditions.append("(content LIKE ? OR preview LIKE ?)")
            params.extend([like, like])
        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        limit_sql = ""
        if limit is not None and int(limit) > 0:
            limit_sql = "LIMIT ? OFFSET ?"
            params.extend([int(limit), max(0, int(offset))])
        with self._lock:
            with self._database.connection(row_factory=SQLiteRow) as conn:
                rows = conn.execute(
                    f"""
                    SELECT id, item_type, content, preview, metadata, pinned, created_at
                    FROM clipboard_history
                    {where_sql}
                    ORDER BY pinned DESC, id DESC
                    {limit_sql}
                    """,
                    tuple(params),
                ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def count(self, query: str = "", *, filter_type: str = "all") -> int:
        q = query.strip()
        filter_value = str(filter_type or "all")
        conditions: list[str] = []
        params: list[object] = []
        if filter_value == "pinned":
            conditions.append("pinned = 1")
        elif filter_value in {"text", "image", "files"}:
            conditions.append("item_type = ?")
            params.append(filter_value)
        if q:
            like = f"%{q}%"
            conditions.append("(content LIKE ? OR preview LIKE ?)")
            params.extend([like, like])
        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._lock:
            with self._database.connection() as conn:
                row = conn.execute(
                    f"SELECT COUNT(*) FROM clipboard_history {where_sql}",
                    tuple(params),
                ).fetchone()
        if row is None:
            return 0
        return int(row[0])

    def get_item(self, item_id: int) -> dict | None:
        with self._lock:
            with self._database.connection(row_factory=SQLiteRow) as conn:
                row = conn.execute(
                    """
                    SELECT id, item_type, content, preview, metadata, pinned, created_at
                    FROM clipboard_history
                    WHERE id = ?
                    """,
                    (item_id,),
                ).fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def latest_item(self) -> dict | None:
        return self.latest_captured_item()

    def latest_captured_item(self) -> dict | None:
        with self._lock:
            with self._database.connection(row_factory=SQLiteRow) as conn:
                row = conn.execute(
                    """
                    SELECT id, item_type, content, preview, metadata, pinned, created_at
                    FROM clipboard_history
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ).fetchone()
        return self._row_to_dict(row) if row is not None else None

    def toggle_pin(self, item_id: int) -> bool | None:
        item = self.get_item(item_id)
        if item is None:
            return None
        next_value = 0 if item["pinned"] else 1
        with self._lock:
            with self._database.connection() as conn:
                conn.execute(
                    "UPDATE clipboard_history SET pinned = ? WHERE id = ?",
                    (next_value, item_id),
                )
        return bool(next_value)

    def clear_all(self) -> bool:
        with self._lock:
            with self._database.connection() as conn:
                row = conn.execute("SELECT COUNT(*) FROM clipboard_history").fetchone()
                if row is None or int(row[0]) <= 0:
                    return False
                conn.execute("DELETE FROM clipboard_history")
        return True

    def clear_unpinned(self) -> bool:
        with self._lock:
            with self._database.connection() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM clipboard_history WHERE pinned = 0"
                ).fetchone()
                if row is None or int(row[0]) <= 0:
                    return False
                conn.execute("DELETE FROM clipboard_history WHERE pinned = 0")
        return True

    def delete_item(self, item_id: int) -> bool:
        with self._lock:
            with self._database.connection() as conn:
                row = conn.execute(
                    "SELECT 1 FROM clipboard_history WHERE id = ?",
                    (item_id,),
                ).fetchone()
                if row is None:
                    return False
                conn.execute("DELETE FROM clipboard_history WHERE id = ?", (item_id,))
        return True

    def get_config(self) -> dict:
        config = DEFAULT_CLIPBOARD_CONFIG.copy()
        for key, value in self._settings.items():
            if key not in config:
                continue
            config[key] = value
        return config

    def get_config_value(self, key: str) -> object:
        return self.get_config().get(key, DEFAULT_CLIPBOARD_CONFIG.get(key))

    def set_config_value(self, key: str, value: object) -> bool:
        if key not in DEFAULT_CLIPBOARD_CONFIG:
            return False
        current = self.get_config_value(key)
        if current == value:
            return False
        self._settings.set(key, value)
        return True

    def should_capture(self, item_type: str, content: str, preview: str) -> bool:
        config = self.get_config()
        if item_type == "text":
            if not config.get("capture_text", True):
                return False
            if not content.strip():
                return False
            max_chars = int(config.get("max_text_chars") or 0)
            if max_chars > 0 and len(content) > max_chars:
                return False
        elif item_type == "image" and not config.get("capture_image", True):
            return False
        elif item_type == "files" and not config.get("capture_files", True):
            return False

        haystack = f"{preview}\n{content}"
        for pattern in config.get("ignore_patterns", []):
            pattern_text = str(pattern).strip()
            if not pattern_text:
                continue
            try:
                if re.search(pattern_text, haystack, re.IGNORECASE):
                    return False
            except re.error:
                if pattern_text.lower() in haystack.lower():
                    return False
        return True

    def close(self) -> None:
        return

    def _ensure_schema(self) -> None:
        with self._lock:
            with self._database.connection(row_factory=SQLiteRow) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS clipboard_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        item_type TEXT NOT NULL DEFAULT 'text',
                        content TEXT NOT NULL DEFAULT '',
                        preview TEXT NOT NULL DEFAULT '',
                        metadata TEXT NOT NULL DEFAULT '{}',
                        pinned INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_clipboard_pinned_id "
                    "ON clipboard_history(pinned DESC, id DESC)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_clipboard_type ON clipboard_history(item_type)"
                )

    @staticmethod
    def _compact_preview(text: str, limit: int = 160) -> str:
        preview = " ".join(text.replace("\r", " ").replace("\n", " ").split())
        if len(preview) > limit:
            return preview[: limit - 3] + "..."
        return preview

    @staticmethod
    def _row_to_dict(row: SQLiteRow) -> dict:
        metadata_raw = row["metadata"] or "{}"
        try:
            metadata = json.loads(metadata_raw)
        except json.JSONDecodeError:
            metadata = {}
        return {
            "id": row["id"],
            "itemType": row["item_type"],
            "content": row["content"],
            "preview": row["preview"],
            "metadata": metadata,
            "pinned": bool(row["pinned"]),
            "createdAt": row["created_at"],
        }

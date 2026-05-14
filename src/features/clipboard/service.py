"""Clipboard background monitoring, history storage, and capture settings."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from app.storage import JsonDictStore, SQLiteDatabase, SQLiteRow, dict_store, sqlite_database
from PySide6.QtCore import QMimeData, QObject, QUrl, Signal
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication


DEFAULT_CLIPBOARD_CONFIG = {
    "capture_text": True,
    "capture_image": True,
    "capture_files": True,
    "max_text_chars": 20000,
    "ignore_patterns": [],
    "hotkey": "Alt+V",
}


class ClipboardHistoryStore(QObject):
    """Persistent clipboard history database shared by background and UI."""

    historyChanged = Signal()
    configChanged = Signal()

    def __init__(
        self,
        database: SQLiteDatabase | Path,
        settings_store: JsonDictStore | None = None,
    ) -> None:
        super().__init__()
        self._database = database if isinstance(database, SQLiteDatabase) else sqlite_database(
            database,
            row_factory=SQLiteRow,
            check_same_thread=False,
        )
        self._db_path = self._database.path
        self._image_dir = self._db_path.parent / "clipboard_assets" / "images"
        self._image_dir.mkdir(parents=True, exist_ok=True)
        self._history_has_legacy_text = False
        self._settings = settings_store or dict_store(
            "clipboard/settings",
            defaults=DEFAULT_CLIPBOARD_CONFIG,
        )
        self._db = self._database.open(row_factory=SQLiteRow, check_same_thread=False)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._db.execute(
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
        columns = {
            row["name"]
            for row in self._db.execute("PRAGMA table_info(clipboard_history)").fetchall()
        }
        self._history_has_legacy_text = "text" in columns
        column_defs = {
            "item_type": "TEXT NOT NULL DEFAULT 'text'",
            "content": "TEXT NOT NULL DEFAULT ''",
            "preview": "TEXT NOT NULL DEFAULT ''",
            "metadata": "TEXT NOT NULL DEFAULT '{}'",
            "pinned": "INTEGER NOT NULL DEFAULT 0",
        }
        for name, ddl in column_defs.items():
            if name not in columns:
                self._db.execute(f"ALTER TABLE clipboard_history ADD COLUMN {name} {ddl}")
        if "text" in columns:
            self._db.execute(
                """
                UPDATE clipboard_history
                SET
                    item_type = COALESCE(NULLIF(item_type, ''), 'text'),
                    content = CASE WHEN content = '' THEN text ELSE content END,
                    preview = CASE WHEN preview = '' THEN text ELSE preview END,
                    metadata = COALESCE(NULLIF(metadata, ''), '{}')
                """
            )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_clipboard_pinned_id "
            "ON clipboard_history(pinned DESC, id DESC)"
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_clipboard_type ON clipboard_history(item_type)"
        )
        self._migrate_settings_from_sqlite()
        self._db.commit()

    def add_text(self, text: str) -> None:
        if not self.should_capture("text", text, text):
            return
        value = text.rstrip("\x00")
        preview = self._compact_preview(value)
        self.add_item("text", value, preview)

    def add_image(self, image: QImage) -> None:
        if image.isNull() or not self.get_config_value("capture_image"):
            return
        file_name = f"{uuid.uuid4().hex}.png"
        image_path = self._image_dir / file_name
        if not image.save(str(image_path), "PNG"):
            return
        metadata = {
            "width": image.width(),
            "height": image.height(),
            "path": str(image_path),
        }
        preview = f"{image.width()} x {image.height()} PNG"
        self.add_item("image", str(image_path), preview, metadata)

    def add_files(self, paths: list[str]) -> None:
        clean_paths = [str(Path(path)) for path in paths if path]
        if not clean_paths:
            return
        names = [Path(path).name or path for path in clean_paths]
        preview = ", ".join(names[:3])
        if len(names) > 3:
            preview += f" ... (+{len(names) - 3})"
        if not self.should_capture("files", json.dumps(clean_paths, ensure_ascii=False), preview):
            return
        self.add_item(
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
    ) -> None:
        if not content:
            return
        latest = self._db.execute(
            "SELECT item_type, content FROM clipboard_history ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if latest and latest["item_type"] == item_type and latest["content"] == content:
            return
        created_at = datetime.now().strftime("%m-%d %H:%M:%S")
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
        if self._history_has_legacy_text:
            self._db.execute(
                """
                INSERT INTO clipboard_history
                    (text, item_type, content, preview, metadata, pinned, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    preview or content,
                    item_type,
                    content,
                    preview,
                    metadata_json,
                    1 if pinned else 0,
                    created_at,
                ),
            )
        else:
            self._db.execute(
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
        self._db.commit()
        self.historyChanged.emit()

    def search(self, query: str) -> list[dict]:
        q = query.strip()
        if not q:
            rows = self._db.execute(
                """
                SELECT id, item_type, content, preview, metadata, pinned, created_at
                FROM clipboard_history
                ORDER BY pinned DESC, id DESC
                LIMIT 100
                """
            ).fetchall()
        else:
            like = f"%{q}%"
            rows = self._db.execute(
                """
                SELECT id, item_type, content, preview, metadata, pinned, created_at
                FROM clipboard_history
                WHERE content LIKE ? OR preview LIKE ?
                ORDER BY pinned DESC, id DESC
                LIMIT 100
                """,
                (like, like),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_item(self, item_id: int) -> dict | None:
        row = self._db.execute(
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
        row = self._db.execute(
            """
            SELECT id, item_type, content, preview, metadata, pinned, created_at
            FROM clipboard_history
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        return self._row_to_dict(row) if row is not None else None

    def toggle_pin(self, item_id: int) -> bool:
        item = self.get_item(item_id)
        if item is None:
            return False
        next_value = 0 if item["pinned"] else 1
        self._db.execute(
            "UPDATE clipboard_history SET pinned = ? WHERE id = ?",
            (next_value, item_id),
        )
        self._db.commit()
        self.historyChanged.emit()
        return bool(next_value)

    def clear_all(self) -> None:
        self._db.execute("DELETE FROM clipboard_history")
        self._db.commit()
        self.historyChanged.emit()

    def delete_item(self, item_id: int) -> None:
        self._db.execute("DELETE FROM clipboard_history WHERE id = ?", (item_id,))
        self._db.commit()
        self.historyChanged.emit()

    def get_config(self) -> dict:
        config = DEFAULT_CLIPBOARD_CONFIG.copy()
        for key, value in self._settings.items():
            if key not in config:
                continue
            config[key] = value
        return config

    def get_config_value(self, key: str) -> object:
        return self.get_config().get(key, DEFAULT_CLIPBOARD_CONFIG.get(key))

    def set_config_value(self, key: str, value: object) -> None:
        if key not in DEFAULT_CLIPBOARD_CONFIG:
            return
        self._settings.set(key, value)
        self.configChanged.emit()

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

    @staticmethod
    def _compact_preview(text: str, limit: int = 160) -> str:
        preview = " ".join(text.replace("\r", " ").replace("\n", " ").split())
        if len(preview) > limit:
            return preview[: limit - 3] + "..."
        return preview

    def _migrate_settings_from_sqlite(self) -> None:
        if self._settings.loaded_from_existing_file:
            return
        table = self._db.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'clipboard_settings'
            """
        ).fetchone()
        if table is None:
            return
        rows = self._db.execute("SELECT key, value FROM clipboard_settings").fetchall()
        values: dict[str, object] = {}
        for row in rows:
            key = str(row["key"])
            if key not in DEFAULT_CLIPBOARD_CONFIG:
                continue
            try:
                values[key] = json.loads(row["value"])
            except json.JSONDecodeError:
                values[key] = DEFAULT_CLIPBOARD_CONFIG[key]
        if values:
            self._settings.set_many(values)

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

    def close(self) -> None:
        self._db.close()


class ClipboardMonitor(QObject):
    """Resident clipboard listener. It should live for the whole app process."""

    def __init__(self, store: ClipboardHistoryStore) -> None:
        super().__init__()
        self._store = store
        self._suppress_next_change = False
        self._last_signature = ""
        self._clipboard = QApplication.clipboard()
        self._clipboard.dataChanged.connect(self._on_change)

    def _on_change(self) -> None:
        if self._suppress_next_change:
            self._suppress_next_change = False
            return

        mime = self._clipboard.mimeData()
        if mime.hasUrls():
            paths = [
                url.toLocalFile()
                for url in mime.urls()
                if url.isLocalFile() and url.toLocalFile()
            ]
            if paths and self._store.get_config_value("capture_files"):
                signature = "files:" + "|".join(paths)
                if signature != self._last_signature:
                    self._last_signature = signature
                    self._store.add_files(paths)
                return

        if mime.hasImage() and self._store.get_config_value("capture_image"):
            image = self._clipboard.image()
            if not image.isNull():
                signature = f"image:{image.cacheKey()}"
                if signature != self._last_signature:
                    self._last_signature = signature
                    self._store.add_image(image)
                return

        text = self._clipboard.text()
        if text:
            signature = f"text:{text}"
        else:
            signature = ""
        if text and signature != self._last_signature:
            self._last_signature = signature
            self._store.add_text(text)

    def copy_text(self, text: str) -> None:
        self._suppress_next_change = True
        self._last_signature = f"text:{text}"
        self._clipboard.setText(text)

    def copy_image(self, image_path: str) -> None:
        image = QImage(image_path)
        if image.isNull():
            return
        self._suppress_next_change = True
        self._last_signature = f"image:{image.cacheKey()}"
        self._clipboard.setImage(image)

    def copy_files(self, paths: list[str]) -> None:
        urls = [QUrl.fromLocalFile(path) for path in paths if path]
        if not urls:
            return
        mime_data = QMimeData()
        mime_data.setUrls(urls)
        self._suppress_next_change = True
        self._last_signature = "files:" + "|".join(paths)
        self._clipboard.setMimeData(mime_data)

    def copy_item(self, item: dict) -> None:
        item_type = item.get("itemType")
        content = str(item.get("content", ""))
        if item_type == "text":
            self.copy_text(content)
        elif item_type == "image":
            self.copy_image(content)
        elif item_type == "files":
            paths = item.get("metadata", {}).get("paths", [])
            if not isinstance(paths, list):
                try:
                    paths = json.loads(content)
                except json.JSONDecodeError:
                    paths = []
            self.copy_files([str(path) for path in paths])

    def stop(self) -> None:
        try:
            self._clipboard.dataChanged.disconnect(self._on_change)
        except RuntimeError:
            pass


class ClipboardBackgroundService:
    """Small service object exposed through PluginContext.services."""

    def __init__(
        self,
        database: SQLiteDatabase | Path,
        settings_store: JsonDictStore | None = None,
    ) -> None:
        self.store = ClipboardHistoryStore(database, settings_store=settings_store)
        self.monitor = ClipboardMonitor(self.store)

    def copy_text(self, text: str) -> None:
        self.monitor.copy_text(text)

    def copy_item(self, item: dict) -> None:
        self.monitor.copy_item(item)

    def copy_item_by_id(self, item_id: int) -> bool:
        item = self.store.get_item(item_id)
        if item is None:
            return False
        self.copy_item(item)
        return True

    def close(self) -> None:
        self.monitor.stop()
        self.store.close()

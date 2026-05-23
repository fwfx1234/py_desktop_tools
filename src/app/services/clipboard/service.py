from __future__ import annotations

import json
from collections.abc import Callable
from threading import RLock

from app.logging import get_logger
from app.storage import DatabaseDictStore, SQLiteDatabase

from .backends.noop_backend import NoopClipboardBackend
from .backends.protocol import ClipboardBackend
from .history_store import ClipboardHistoryStore
from .models import DEFAULT_CLIPBOARD_CONFIG


class ClipboardService:
    def __init__(
        self,
        database: SQLiteDatabase,
        settings_store: DatabaseDictStore | None = None,
        *,
        backend: ClipboardBackend | None = None,
    ) -> None:
        self.store = ClipboardHistoryStore(database, settings_store=settings_store)
        self._backend = backend or NoopClipboardBackend()
        self._history_listeners: list[Callable[[], None]] = []
        self._config_listeners: list[Callable[[], None]] = []
        self._listener_lock = RLock()
        self._started = False
        self._log = get_logger("app.services.clipboard")

    def start(self) -> None:
        if self._started:
            return
        try:
            self._backend.start(self._handle_backend_change)
        except Exception as exc:
            self._log.warning("clipboard.backend.start_failed", "剪贴板 backend 启动失败", error=str(exc))
            raise
        self._started = True
        self._log.debug("clipboard.service.start", "剪贴板服务启动", backend=type(self._backend).__name__)

    def add_history_listener(self, callback: Callable[[], None]) -> None:
        with self._listener_lock:
            if callback not in self._history_listeners:
                self._history_listeners.append(callback)

    def remove_history_listener(self, callback: Callable[[], None]) -> None:
        with self._listener_lock:
            if callback in self._history_listeners:
                self._history_listeners.remove(callback)

    def add_config_listener(self, callback: Callable[[], None]) -> None:
        with self._listener_lock:
            if callback not in self._config_listeners:
                self._config_listeners.append(callback)

    def remove_config_listener(self, callback: Callable[[], None]) -> None:
        with self._listener_lock:
            if callback in self._config_listeners:
                self._config_listeners.remove(callback)

    def search(
        self,
        query: str,
        *,
        filter_type: str = "all",
        offset: int = 0,
        limit: int | None = None,
    ) -> list[dict]:
        return self.store.search(
            query,
            filter_type=filter_type,
            offset=offset,
            limit=limit,
        )

    def count(self, query: str = "", *, filter_type: str = "all") -> int:
        return self.store.count(query, filter_type=filter_type)

    def promote_item(self, item_id: int) -> bool:
        promoted = self.store.promote_item(item_id)
        if promoted:
            self._notify_history_changed()
        return promoted

    def latest_item(self) -> dict | None:
        return self.store.latest_item()

    def latest_captured_item(self) -> dict | None:
        return self.store.latest_captured_item()

    def latest_context_item(self) -> dict | None:
        return self.latest_captured_item() or self.latest_item()

    def read_live_item(self) -> dict | None:
        """Read the current system pasteboard directly, bypassing history capture.

        Returns a dict shaped like the history items (``itemType`` + ``content``
        + ``metadata``) when something is on the pasteboard, otherwise ``None``.
        Used by plugins that need the freshest clipboard content without
        depending on the watcher having caught it yet.
        """
        backend = getattr(self, "_backend", None)
        read_current = getattr(backend, "read_current", None)
        if not callable(read_current):
            return None
        try:
            draft = read_current()
        except Exception:
            return None
        if draft is None:
            return None
        item_type = getattr(draft, "item_type", "")
        content = getattr(draft, "content", "") or ""
        metadata = dict(getattr(draft, "metadata", {}) or {})
        if item_type == "image" and not content:
            image_bytes = getattr(draft, "image_bytes", b"") or b""
            if image_bytes:
                cached = self._cache_live_image(image_bytes)
                if cached:
                    content = cached
        if not content and item_type != "image":
            return None
        return {
            "itemType": item_type,
            "content": content,
            "metadata": metadata,
        }

    def _cache_live_image(self, image_bytes: bytes) -> str:
        try:
            target_dir = self.store.image_dir
            target_dir.mkdir(parents=True, exist_ok=True)
            from hashlib import sha1

            digest = sha1(image_bytes).hexdigest()[:12]
            target = target_dir / f"live_{digest}.png"
            if not target.exists():
                target.write_bytes(image_bytes)
            return str(target)
        except Exception:
            return ""

    def get_item(self, item_id: int) -> dict | None:
        return self.store.get_item(item_id)

    def toggle_pin(self, item_id: int) -> bool:
        pinned = self.store.toggle_pin(item_id)
        if pinned is None:
            return False
        self._notify_history_changed()
        return pinned

    def clear_all(self) -> bool:
        cleared = self.store.clear_all()
        if cleared:
            self._notify_history_changed()
        return cleared

    def clear_unpinned(self) -> bool:
        cleared = self.store.clear_unpinned()
        if cleared:
            self._notify_history_changed()
        return cleared

    def delete_item(self, item_id: int) -> bool:
        deleted = self.store.delete_item(item_id)
        if deleted:
            self._notify_history_changed()
        return deleted

    def get_config(self) -> dict:
        return self.store.get_config()

    def get_config_value(self, key: str) -> object:
        return self.store.get_config_value(key)

    def set_config_value(self, key: str, value: object) -> bool:
        updated = self.store.set_config_value(key, value)
        if updated:
            self._notify_config_changed()
        return updated

    def copy_text(self, text: str) -> bool:
        try:
            self._backend.write_text(text)
        except Exception as exc:
            self._log.warning("clipboard.copy_text_failed", "剪贴板文本写入失败", error=str(exc), textLength=len(text or ""))
            return False
        return True

    def copy_item(self, item: dict) -> bool:
        item_type = item.get("itemType")
        content = str(item.get("content", ""))
        try:
            if item_type == "text":
                self._backend.write_text(content)
            elif item_type == "image":
                self._backend.write_image(content)
            elif item_type == "files":
                paths = item.get("metadata", {}).get("paths", [])
                if not isinstance(paths, list):
                    paths = _parse_paths(content)
                self._backend.write_files([str(path) for path in paths])
            else:
                return False
        except Exception as exc:
            self._log.warning("clipboard.copy_item_failed", "剪贴板记录写回失败", itemType=str(item_type), error=str(exc))
            return False
        return True

    def copy_item_by_id(self, item_id: int) -> bool:
        item = self.store.get_item(item_id)
        if item is None:
            return False
        copied = self.copy_item(item)
        if copied:
            self.promote_item(item_id)
        return copied

    def close(self) -> None:
        try:
            self._backend.stop()
        except Exception as exc:
            self._log.warning("clipboard.backend.stop_failed", "剪贴板 backend 停止失败", error=str(exc))
        self.store.close()
        self._started = False
        self._log.debug("clipboard.service.stop", "剪贴板服务停止")

    def _handle_backend_change(self, draft) -> None:
        try:
            captured = self.store.capture_draft(draft)
        except Exception as exc:
            self._log.warning("clipboard.capture_failed", "剪贴板记录捕获失败", error=str(exc))
            return
        if captured:
            self._log.debug("clipboard.capture", "剪贴板记录已捕获", itemType=getattr(draft, "item_type", ""))
            self._notify_history_changed()

    def _notify_history_changed(self) -> None:
        with self._listener_lock:
            listeners = list(self._history_listeners)
        for callback in listeners:
            callback()

    def _notify_config_changed(self) -> None:
        with self._listener_lock:
            listeners = list(self._config_listeners)
        for callback in listeners:
            callback()


def _parse_paths(content: str) -> list[str]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]


__all__ = [
    "ClipboardService",
    "ClipboardHistoryStore",
    "DEFAULT_CLIPBOARD_CONFIG",
]

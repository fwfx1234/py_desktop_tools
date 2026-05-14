from __future__ import annotations

import json
import re
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from .service import ClipboardBackgroundService


class ClipboardWindowViewModel(QObject):
    """ViewModel for clipboard history, details, and capture settings UI."""

    historyChanged = Signal("QVariantList")
    configChanged = Signal("QVariantMap")
    messageChanged = Signal(str)

    def __init__(
        self,
        service: ClipboardBackgroundService,
        *,
        initial_panel: str = "history",
        initial_query: str = "",
    ) -> None:
        super().__init__()
        self._service = service
        self._query = initial_query
        self._initial_panel = initial_panel
        self._service.store.historyChanged.connect(self._emit_history)
        self._service.store.configChanged.connect(self._emit_config)

    @Slot(result=str)
    def initialPanel(self) -> str:
        return self._initial_panel

    @Slot(result=str)
    def initialQuery(self) -> str:
        return self._query

    @Slot(str)
    def refreshHistory(self, query: str = "") -> None:
        self._query = query
        self._emit_history()

    @Slot()
    def loadConfig(self) -> None:
        self._emit_config()

    @Slot(str)
    def copyItem(self, item_id: str) -> None:
        db_id = self._parse_id(item_id)
        if db_id is None:
            return
        if self._service.copy_item_by_id(db_id):
            self.messageChanged.emit("已写回系统剪切板")

    @Slot(str)
    def togglePin(self, item_id: str) -> None:
        db_id = self._parse_id(item_id)
        if db_id is None:
            return
        pinned = self._service.store.toggle_pin(db_id)
        self.messageChanged.emit("已置顶" if pinned else "已取消置顶")

    @Slot(str)
    def deleteItem(self, item_id: str) -> None:
        db_id = self._parse_id(item_id)
        if db_id is None:
            return
        self._service.store.delete_item(db_id)
        self.messageChanged.emit("已删除")

    @Slot()
    def clearHistory(self) -> None:
        self._service.store.clear_all()
        self.messageChanged.emit("剪切板历史已清空")

    @Slot(bool)
    def setCaptureText(self, value: bool) -> None:
        self._service.store.set_config_value("capture_text", bool(value))

    @Slot(bool)
    def setCaptureImage(self, value: bool) -> None:
        self._service.store.set_config_value("capture_image", bool(value))

    @Slot(bool)
    def setCaptureFiles(self, value: bool) -> None:
        self._service.store.set_config_value("capture_files", bool(value))

    @Slot(str)
    def saveIgnorePatterns(self, text: str) -> None:
        patterns = [
            part.strip()
            for part in re.split(r"[|\n]", text)
            if part.strip()
        ]
        self._service.store.set_config_value("ignore_patterns", patterns)
        self.messageChanged.emit("过滤规则已保存")

    @Slot()
    def clearIgnorePatterns(self) -> None:
        self._service.store.set_config_value("ignore_patterns", [])
        self.messageChanged.emit("过滤规则已清空")

    @Slot(str)
    def saveMaxTextChars(self, text: str) -> None:
        try:
            max_chars = max(0, int(text.strip()))
        except ValueError:
            self.messageChanged.emit("文本长度上限需要是数字")
            return
        self._service.store.set_config_value("max_text_chars", max_chars)
        self.messageChanged.emit("文本长度上限已保存")

    @Slot(str)
    def saveHotkey(self, text: str) -> None:
        hotkey = normalize_hotkey(text)
        if not hotkey:
            self.messageChanged.emit("快捷键格式无效")
            return
        self._service.store.set_config_value("hotkey", hotkey)
        self.messageChanged.emit(f"剪切板快捷键已保存为 {hotkey}")

    def close(self) -> None:
        try:
            self._service.store.historyChanged.disconnect(self._emit_history)
        except RuntimeError:
            pass
        try:
            self._service.store.configChanged.disconnect(self._emit_config)
        except RuntimeError:
            pass

    def deleteLater(self) -> None:
        self.close()
        super().deleteLater()

    def _emit_history(self) -> None:
        self.historyChanged.emit(
            [self._to_view_item(row) for row in self._service.store.search(self._query)]
        )

    def _emit_config(self) -> None:
        config = self._service.store.get_config()
        self.configChanged.emit(
            {
                "capture_text": bool(config.get("capture_text", True)),
                "capture_image": bool(config.get("capture_image", True)),
                "capture_files": bool(config.get("capture_files", True)),
                "max_text_chars": str(config.get("max_text_chars") or 0),
                "ignore_patterns": " | ".join(
                    str(item) for item in config.get("ignore_patterns", [])
                ),
                "hotkey": str(config.get("hotkey") or ""),
            }
        )

    @staticmethod
    def _to_view_item(row: dict) -> dict:
        item_type = str(row.get("itemType", "text"))
        metadata = row.get("metadata", {})
        preview = str(row.get("preview") or row.get("content") or "")
        content = str(row.get("content") or "")
        created_at = str(row.get("createdAt") or "")
        pinned = bool(row.get("pinned"))

        if item_type == "image":
            width = metadata.get("width", "")
            height = metadata.get("height", "")
            title = f"图片 {width} x {height}".strip()
            subtitle = "图片"
            if width and height:
                subtitle = f"图片 · {width} x {height}"
            detail = content
            image_url = _file_url(content)
            icon = "qta:mdi6.image-outline"
            type_label = "图片"
        elif item_type == "files":
            paths = metadata.get("paths", [])
            if not isinstance(paths, list):
                paths = _parse_paths(content)
            names = [Path(str(path)).name or str(path) for path in paths]
            title = ", ".join(names[:3]) if names else "文件"
            if len(names) > 3:
                title += f" ... (+{len(names) - 3})"
            subtitle = f"文件 · {len(paths)} 个" if paths else "文件"
            detail = "\n".join(str(path) for path in paths)
            image_url = ""
            icon = "qta:mdi6.file-multiple-outline"
            type_label = "文件"
        else:
            title = preview or "(空文本)"
            subtitle = "文本"
            detail = content
            image_url = ""
            icon = "qta:mdi6.clipboard-text-outline"
            type_label = "文本"

        return {
            "id": str(row.get("id", "")),
            "title": title,
            "subtitle": subtitle,
            "preview": preview,
            "content": content,
            "detail": detail,
            "itemType": item_type,
            "typeLabel": type_label,
            "icon": icon,
            "createdAt": created_at,
            "pinned": pinned,
            "metadata": metadata,
            "imageUrl": image_url,
        }

    @staticmethod
    def _parse_id(item_id: str) -> int | None:
        try:
            return int(item_id)
        except (TypeError, ValueError):
            return None


def normalize_hotkey(text: str) -> str:
    aliases = {
        "control": "Ctrl",
        "ctrl": "Ctrl",
        "alt": "Alt",
        "shift": "Shift",
        "win": "Win",
        "meta": "Win",
        "cmd": "Win",
        "space": "Space",
        "esc": "Esc",
        "escape": "Esc",
        "return": "Enter",
    }
    parts = [part.strip() for part in text.replace("＋", "+").split("+") if part.strip()]
    if not parts:
        return ""
    normalized: list[str] = []
    for part in parts:
        key = aliases.get(part.lower(), part.upper() if len(part) == 1 else part.title())
        normalized.append(key)
    key = normalized[-1]
    modifiers = [part for part in normalized[:-1] if part in {"Ctrl", "Alt", "Shift", "Win"}]
    if not key or key in {"Ctrl", "Alt", "Shift", "Win"}:
        return ""
    ordered_modifiers = [item for item in ["Ctrl", "Alt", "Shift", "Win"] if item in modifiers]
    return "+".join(ordered_modifiers + [key])


def _file_url(path: str) -> str:
    if not path:
        return ""
    return "file:///" + str(Path(path)).replace("\\", "/")


def _parse_paths(content: str) -> list[str]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]

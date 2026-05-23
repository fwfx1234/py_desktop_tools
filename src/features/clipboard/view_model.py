from __future__ import annotations

import json
import re
from pathlib import Path

from PySide6.QtCore import (
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    Property,
    Qt,
    Signal,
    Slot,
)

from app.services.clipboard import ClipboardService


_PAGE_SIZE = 80
_ItemRole = Qt.UserRole + 1


class ClipboardHistoryModel(QAbstractListModel):
    countChanged = Signal()
    hasMoreChanged = Signal()
    activeFilterChanged = Signal()

    def __init__(self, service: ClipboardService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._items: list[dict] = []
        self._query = ""
        self._filter = "all"
        self._has_more = True
        self._latest_id = 0

    def roleNames(self) -> dict:
        return {_ItemRole: QByteArray(b"item")}

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        if row < 0 or row >= len(self._items):
            return None
        if role == _ItemRole:
            return self._items[row]
        return None

    def canFetchMore(self, parent: QModelIndex = QModelIndex()) -> bool:
        if parent.isValid():
            return False
        return self._has_more

    def fetchMore(self, parent: QModelIndex = QModelIndex()) -> None:
        if parent.isValid():
            return
        self._fetch_next_page()

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._items)

    @Property(bool, notify=hasMoreChanged)
    def hasMore(self) -> bool:
        return self._has_more

    @Property(str, notify=activeFilterChanged)
    def activeFilter(self) -> str:
        return self._filter

    @Slot()
    def loadMore(self) -> None:
        self._fetch_next_page()

    @Slot(int, result="QVariant")
    def itemAt(self, row: int):
        if row < 0 or row >= len(self._items):
            return {}
        return self._items[row]

    @Slot(str, result=int)
    def indexOfId(self, item_id: str) -> int:
        if not item_id:
            return -1
        key = str(item_id)
        for i, item in enumerate(self._items):
            if str(item.get("id", "")) == key:
                return i
        return -1

    @Slot(str, result="QVariant")
    def itemById(self, item_id: str):
        idx = self.indexOfId(item_id)
        if idx < 0:
            return {}
        return self._items[idx]

    def reset(self, query: str, filter_type: str) -> None:
        self.beginResetModel()
        self._items.clear()
        self._query = query
        self._filter = filter_type
        self._has_more = True
        self._latest_id = self._fetch_latest_db_id()
        self.endResetModel()
        self.countChanged.emit()
        self.hasMoreChanged.emit()
        self.activeFilterChanged.emit()
        self._fetch_next_page()

    def apply_history_changed(self) -> None:
        latest = self._service.latest_item()
        if latest is None:
            return
        try:
            latest_id = int(latest.get("id"))
        except (TypeError, ValueError):
            latest_id = 0
        if latest_id == 0 or latest_id == self._latest_id:
            return
        self._latest_id = latest_id
        latest_view = _to_view_item(latest)
        if not self._matches_filter(latest_view):
            return
        existing = self.indexOfId(latest_view.get("id", ""))
        if existing >= 0:
            self.beginRemoveRows(QModelIndex(), existing, existing)
            self._items.pop(existing)
            self.endRemoveRows()
        insertion = self._insertion_index(latest_view)
        self.beginInsertRows(QModelIndex(), insertion, insertion)
        self._items.insert(insertion, latest_view)
        self.endInsertRows()
        self.countChanged.emit()

    def remove_id(self, item_id: str) -> None:
        idx = self.indexOfId(item_id)
        if idx < 0:
            return
        self.beginRemoveRows(QModelIndex(), idx, idx)
        self._items.pop(idx)
        self.endRemoveRows()
        self.countChanged.emit()

    def update_pinned(self, item_id: str, pinned: bool) -> None:
        idx = self.indexOfId(item_id)
        if idx < 0:
            return
        if bool(self._items[idx].get("pinned")) == bool(pinned):
            return
        item = dict(self._items[idx])
        item["pinned"] = bool(pinned)
        self._items[idx] = item
        model_index = self.index(idx, 0)
        self.dataChanged.emit(model_index, model_index, [_ItemRole])

    def remove_unpinned(self) -> None:
        if not self._items:
            return
        i = len(self._items) - 1
        while i >= 0:
            if not self._items[i].get("pinned"):
                self.beginRemoveRows(QModelIndex(), i, i)
                self._items.pop(i)
                self.endRemoveRows()
            i -= 1
        self.countChanged.emit()

    def clear(self) -> None:
        if not self._items and not self._has_more:
            return
        self.beginResetModel()
        self._items.clear()
        self._has_more = False
        self.endResetModel()
        self.countChanged.emit()
        self.hasMoreChanged.emit()

    def _fetch_next_page(self) -> None:
        if not self._has_more:
            return
        rows = self._service.search(
            self._query,
            filter_type=self._filter,
            offset=len(self._items),
            limit=_PAGE_SIZE,
        )
        items = [_to_view_item(row) for row in rows]
        if not items:
            if self._has_more:
                self._has_more = False
                self.hasMoreChanged.emit()
            return
        start = len(self._items)
        self.beginInsertRows(QModelIndex(), start, start + len(items) - 1)
        self._items.extend(items)
        self.endInsertRows()
        self.countChanged.emit()
        if len(items) < _PAGE_SIZE:
            self._has_more = False
            self.hasMoreChanged.emit()

    def _matches_filter(self, item: dict) -> bool:
        if self._filter == "pinned" and not item.get("pinned"):
            return False
        if self._filter in {"text", "image", "files"} and str(item.get("itemType", "")) != self._filter:
            return False
        q = self._query.strip().lower()
        if q:
            haystack = " ".join(
                str(item.get(field, ""))
                for field in ("title", "subtitle", "preview", "content", "detail")
            ).lower()
            if q not in haystack:
                return False
        return True

    def _insertion_index(self, item: dict) -> int:
        del item
        return 0

    def _fetch_latest_db_id(self) -> int:
        latest = self._service.latest_item()
        if latest is None:
            return 0
        try:
            return int(latest.get("id"))
        except (TypeError, ValueError):
            return 0


class ClipboardWindowViewModel(QObject):
    """ViewModel for clipboard history, details, and capture settings UI."""

    historyModelChanged = Signal()
    configChanged = Signal("QVariantMap")
    messageChanged = Signal(str)
    openStateChanged = Signal("QVariantMap")

    def __init__(
        self,
        service: ClipboardService,
        *,
        initial_panel: str = "history",
        initial_query: str = "",
    ) -> None:
        super().__init__()
        self._service = service
        self._query = initial_query
        self._initial_panel = initial_panel
        self._filter_type = "all"
        self._history_model = ClipboardHistoryModel(service, self)
        self._service.add_history_listener(self._on_history_changed)
        self._service.add_config_listener(self._emit_config)

    @Property(QObject, notify=historyModelChanged)
    def historyModel(self) -> ClipboardHistoryModel:
        return self._history_model

    @Slot(result=str)
    def initialPanel(self) -> str:
        return self._initial_panel

    @Slot(result=str)
    def initialQuery(self) -> str:
        return self._query

    @Slot(result=str)
    def latestItemId(self) -> str:
        latest = self._service.latest_item()
        if latest is None:
            return ""
        return str(latest.get("id") or "")

    @Slot(str)
    def refreshHistory(self, query: str = "") -> None:
        self._query = query
        self._history_model.reset(self._query, self._filter_type)

    @Slot(str)
    def setFilterType(self, filter_type: str) -> None:
        value = str(filter_type or "all")
        if value not in {"all", "pinned", "text", "image", "files"}:
            value = "all"
        if self._filter_type == value:
            return
        self._filter_type = value
        self._history_model.reset(self._query, self._filter_type)

    @Slot()
    def resetToLatest(self) -> None:
        self._query = ""
        self._initial_panel = "history"
        self._filter_type = "all"
        self._history_model.reset("", "all")
        self.openStateChanged.emit(
            {
                "panel": "history",
                "query": "",
                "filter": "all",
                "latestItemId": self.latestItemId(),
            }
        )

    @Slot()
    def showSettingsPanel(self) -> None:
        self._initial_panel = "settings"
        self.openStateChanged.emit(
            {
                "panel": "settings",
                "query": "",
                "filter": "all",
                "latestItemId": self.latestItemId(),
            }
        )

    @Slot()
    def loadConfig(self) -> None:
        self._emit_config()

    @Slot(str)
    def copyItem(self, item_id: str) -> None:
        db_id = self._parse_id(item_id)
        if db_id is None:
            return
        if self._service.copy_item_by_id(db_id):
            self.messageChanged.emit("已写回系统剪贴板")
        else:
            self.messageChanged.emit("写入剪贴板失败")

    @Slot(str)
    def togglePin(self, item_id: str) -> None:
        db_id = self._parse_id(item_id)
        if db_id is None:
            return
        pinned = self._service.toggle_pin(db_id)
        self._history_model.update_pinned(item_id, bool(pinned))
        self.messageChanged.emit("已置顶" if pinned else "已取消置顶")

    @Slot(str)
    def deleteItem(self, item_id: str) -> None:
        db_id = self._parse_id(item_id)
        if db_id is None:
            return
        if self._service.delete_item(db_id):
            self._history_model.remove_id(item_id)
        self.messageChanged.emit("已删除")

    @Slot()
    def clearHistory(self) -> None:
        if self._service.clear_all():
            self._history_model.clear()
        self.messageChanged.emit("剪贴板历史已清空")

    @Slot()
    def clearUnpinned(self) -> None:
        if self._service.clear_unpinned():
            self._history_model.remove_unpinned()
            self.messageChanged.emit("未置顶记录已清空")
        else:
            self.messageChanged.emit("没有可清空的未置顶记录")

    @Slot(bool)
    def setCaptureText(self, value: bool) -> None:
        self._service.set_config_value("capture_text", bool(value))

    @Slot(bool)
    def setCaptureImage(self, value: bool) -> None:
        self._service.set_config_value("capture_image", bool(value))

    @Slot(bool)
    def setCaptureFiles(self, value: bool) -> None:
        self._service.set_config_value("capture_files", bool(value))

    @Slot(str)
    def saveIgnorePatterns(self, text: str) -> None:
        patterns = [
            part.strip()
            for part in re.split(r"[|\n]", text)
            if part.strip()
        ]
        self._service.set_config_value("ignore_patterns", patterns)
        self.messageChanged.emit("过滤规则已保存")

    @Slot()
    def clearIgnorePatterns(self) -> None:
        self._service.set_config_value("ignore_patterns", [])
        self.messageChanged.emit("过滤规则已清空")

    @Slot(str)
    def saveMaxTextChars(self, text: str) -> None:
        try:
            max_chars = max(0, int(text.strip()))
        except ValueError:
            self.messageChanged.emit("文本长度上限需要是数字")
            return
        self._service.set_config_value("max_text_chars", max_chars)
        self.messageChanged.emit("文本长度上限已保存")

    @Slot(str)
    def saveHotkey(self, text: str) -> None:
        hotkey = normalize_hotkey(text)
        if not hotkey:
            self.messageChanged.emit("快捷键格式无效")
            return
        self._service.set_config_value("hotkey", hotkey)
        self.messageChanged.emit(f"剪贴板快捷键已保存为 {hotkey}")

    def dispose(self) -> None:
        self._service.remove_history_listener(self._on_history_changed)
        self._service.remove_config_listener(self._emit_config)

    # Backwards-compatible alias used by tests and legacy callers.
    close = dispose

    def deleteLater(self) -> None:
        self.dispose()
        super().deleteLater()

    def _on_history_changed(self) -> None:
        self._history_model.apply_history_changed()

    def _emit_config(self) -> None:
        config = self._service.get_config()
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
    def _parse_id(item_id: str) -> int | None:
        try:
            return int(item_id)
        except (TypeError, ValueError):
            return None


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
        title = f"图片 {width} x {height}" if width and height else "图片"
        subtitle = "图片"
        if width and height:
            subtitle = f"图片 · {width} x {height}"
        detail = content
        image_url = _file_url(content)
        icon = "qta:mdi6.image-outline"
        type_label = "图片"
        badges = ["图片"]
        stats = f"{width} x {height}" if width and height else "图片"
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
        badges = ["文件"]
        stats = f"{len(paths)} 个文件" if paths else "文件"
    else:
        title = preview or "(空文本)"
        badges = _text_badges(content)
        subtitle = "文本"
        if badges:
            subtitle = "文本 · " + " · ".join(badges[:2])
        detail = content
        image_url = ""
        icon = _text_icon(content)
        type_label = "文本"
        stats = _text_stats(content)

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
        "badges": badges,
        "stats": stats,
    }


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


def _text_badges(text: str) -> list[str]:
    value = text.strip()
    if not value:
        return []
    badges: list[str] = []
    lowered = value.lower()
    if re.match(r"^https?://\S+$", value):
        badges.append("链接")
    elif re.match(r"^[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}$", value):
        badges.append("邮箱")
    elif _looks_like_json(value):
        badges.append("JSON")
    elif "\n" in value:
        badges.append("多行")
    if any(token in lowered for token in ["password", "token", "secret", "apikey", "api_key"]):
        badges.append("敏感")
    return badges[:3]


def _text_icon(text: str) -> str:
    badges = _text_badges(text)
    if "链接" in badges:
        return "qta:mdi6.link-variant"
    if "邮箱" in badges:
        return "qta:mdi6.email-outline"
    if "JSON" in badges:
        return "qta:mdi6.code-json"
    if "敏感" in badges:
        return "qta:mdi6.shield-key-outline"
    return "qta:mdi6.clipboard-text-outline"


def _text_stats(text: str) -> str:
    chars = len(text)
    lines = len(text.splitlines()) if text else 0
    if lines > 1:
        return f"{chars} 字符 · {lines} 行"
    return f"{chars} 字符"


def _looks_like_json(text: str) -> bool:
    value = text.strip()
    if not (
        (value.startswith("{") and value.endswith("}"))
        or (value.startswith("[") and value.endswith("]"))
    ):
        return False
    try:
        json.loads(value)
    except json.JSONDecodeError:
        return False
    return True


def _file_url(path: str) -> str:
    if not path:
        return ""
    normalized = str(path).strip()
    if not normalized:
        return ""
    value = normalized.replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", value):
        return "file:///" + value
    try:
        return Path(normalized).resolve().as_uri()
    except ValueError:
        if value.startswith("/"):
            return "file://" + value
        return "file:///" + value


def _parse_paths(content: str) -> list[str]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtWidgets import QApplication

from .models import PlatformResult


class QtClipboardApi:
    def read_text(self) -> str:
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return ""
        return clipboard.text()

    def write_text(self, text: str) -> PlatformResult:
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return PlatformResult(False, "剪贴板不可用", "unavailable")
        clipboard.setText(text)
        return PlatformResult(True, data={"type": "text"})

    def clear(self) -> PlatformResult:
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return PlatformResult(False, "剪贴板不可用", "unavailable")
        clipboard.clear()
        return PlatformResult(True)

    def write_files(self, paths: list[str | Path]) -> PlatformResult:
        clean_paths = [Path(path) for path in paths if str(path)]
        if not clean_paths:
            return PlatformResult(False, "文件列表为空", "invalid")
        missing = [str(path) for path in clean_paths if not path.exists()]
        if missing:
            return PlatformResult(False, "文件不存在", "not_found", {"missing": missing})
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return PlatformResult(False, "剪贴板不可用", "unavailable")
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(path)) for path in clean_paths])
        clipboard.setMimeData(mime)
        return PlatformResult(True, data={"type": "files", "count": len(clean_paths)})

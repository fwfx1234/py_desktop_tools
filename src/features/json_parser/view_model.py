from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from .service import JsonService


class JsonParserViewModel(QObject):
    resultUpdated = Signal("QVariantMap")
    jsonCopied = Signal(bool, str)
    inputTextChanged = Signal(str)
    inputFilled = Signal(str)
    statusMessage = Signal(str, str)

    def __init__(self, initial_text: str = "", platform_api: object | None = None) -> None:
        super().__init__()
        self._service = JsonService()
        self._platform = platform_api
        self._input_text = initial_text

    @Slot(result=str)
    def initialText(self) -> str:
        return self._input_text

    @Slot(str)
    def setInputText(self, text: str) -> None:
        if self._input_text == text:
            return
        self._input_text = text
        self.inputTextChanged.emit(text)

    @Slot(str)
    def formatJson(self, text: str) -> None:
        self._emit(self._service.format(text), mode="format")

    @Slot(str)
    def compressJson(self, text: str) -> None:
        self._emit(self._service.compress(text), mode="compress")

    @Slot(str, str)
    def queryJson(self, text: str, expression: str) -> None:
        self._emit(self._service.query(text, expression), mode="query")

    @Slot(str, str)
    def processJson(self, jsonText: str, query: str) -> None:
        if query.strip():
            self.queryJson(jsonText, query)
        else:
            self.formatJson(jsonText)

    @Slot(str)
    def copyText(self, text: str) -> None:
        if not text:
            self.jsonCopied.emit(False, "无可复制内容")
            return
        ok = self._write_clipboard(text)
        if ok:
            self.jsonCopied.emit(True, "已复制到剪贴板")
        else:
            self.jsonCopied.emit(False, "复制失败")

    @Slot()
    def fillFromClipboard(self) -> None:
        if self._platform is None:
            self.statusMessage.emit("剪贴板不可用", "error")
            return
        try:
            text = self._platform.clipboard.read_text() or ""
        except Exception:
            text = ""
        if not text.strip():
            self.statusMessage.emit("剪贴板为空", "info")
            return
        self.setInputText(text)
        self.inputFilled.emit(text)

    def _emit(self, result, *, mode: str) -> None:
        payload = {
            "output": result.output,
            "error": result.error,
            "errorLine": result.error_line,
            "errorColumn": result.error_column,
            "errorPhase": result.error_phase,
            "charCount": result.char_count,
            "lineCount": result.line_count,
            "kind": result.kind,
            "size": result.size,
            "depth": result.depth,
            "mode": mode,
        }
        self.resultUpdated.emit(payload)

    def _write_clipboard(self, text: str) -> bool:
        if self._platform is None:
            return False
        try:
            result = self._platform.clipboard.write_text(text)
        except Exception:
            return False
        return bool(getattr(result, "success", False))

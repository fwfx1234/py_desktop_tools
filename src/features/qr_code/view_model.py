from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from .service import QrService, normalize_local_path


class QrViewModel(QObject):
    previewUpdated = Signal(str)
    qrSaved = Signal(bool, str, str)
    qrCopied = Signal(bool, str)
    qrScanFinished = Signal(str, str)
    qrHistoryUpdated = Signal("QVariantList")
    qrHistoryExported = Signal(bool, str)
    qrSaveRootRevealed = Signal(bool, str)
    inputTextChanged = Signal(str)

    def __init__(self, initial_text: str = "", platform_api: object | None = None) -> None:
        super().__init__()
        self._service = QrService()
        self._platform = platform_api
        self._input_text = initial_text
        self._disposed = False

    def dispose(self) -> None:
        self._disposed = True
        self._service = None
        self._platform = None

    @Slot(result=str)
    def initialText(self) -> str:
        return self._input_text

    @Slot(result=str)
    def saveRoot(self) -> str:
        return str(self._service.save_root)

    @Slot(str)
    def setInputText(self, text: str) -> None:
        if self._input_text == text:
            return
        self._input_text = text
        self.inputTextChanged.emit(text)

    @Slot(str)
    def previewQr(self, content: str) -> None:
        self.previewUpdated.emit(self._service.preview(content))

    @Slot(str)
    def saveQr(self, content: str) -> None:
        path, error = self._service.save(content)
        if error:
            self.qrSaved.emit(False, "", error)
            return
        self.qrSaved.emit(True, path, f"已保存到: {path}")
        self.qrHistoryUpdated.emit(self._service.get_history())

    @Slot(str)
    def copyQrContent(self, content: str) -> None:
        if not content.strip():
            self.qrCopied.emit(False, "无可复制内容")
            return
        ok = self._write_clipboard(content)
        if ok:
            self._service.record_copy(content)
            self.qrCopied.emit(True, "已复制内容")
            self.qrHistoryUpdated.emit(self._service.get_history())
        else:
            self.qrCopied.emit(False, "复制失败")

    @Slot(str)
    def scanQrImage(self, imagePath: str) -> None:
        cleaned = normalize_local_path(imagePath)
        text, error = self._service.scan(cleaned)
        self.qrScanFinished.emit(text, error)
        if text:
            self.qrHistoryUpdated.emit(self._service.get_history())

    @Slot()
    def clearQrHistory(self) -> None:
        self._service.clear_history()
        self.qrHistoryUpdated.emit(self._service.get_history())

    @Slot(str)
    def removeHistoryItem(self, itemId: str) -> None:
        self._service.remove_history(itemId)
        self.qrHistoryUpdated.emit(self._service.get_history())

    @Slot()
    def exportQrHistoryAuto(self) -> None:
        path, error = self._service.export()
        if error:
            self.qrHistoryExported.emit(False, error)
        else:
            self.qrHistoryExported.emit(True, f"已导出到: {path}")

    @Slot(str)
    def exportQrHistory(self, savePath: str) -> None:
        path, error = self._service.export(normalize_local_path(savePath))
        if error:
            self.qrHistoryExported.emit(False, error)
        else:
            self.qrHistoryExported.emit(True, f"已导出到: {path}")

    @Slot()
    def revealSaveRoot(self) -> None:
        target = self._service.save_root
        try:
            target.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self.qrSaveRootRevealed.emit(False, f"无法访问目录: {exc}")
            return
        if self._platform is None:
            self.qrSaveRootRevealed.emit(False, "平台 API 不可用")
            return
        result = self._platform.open_path(target)
        success = getattr(result, "success", False)
        message = getattr(result, "message", "") or str(target)
        if success:
            self.qrSaveRootRevealed.emit(True, str(target))
        else:
            self.qrSaveRootRevealed.emit(False, message or "打开目录失败")

    @Slot()
    def fillFromClipboard(self) -> None:
        if self._platform is None:
            return
        try:
            text = self._platform.clipboard.read_text() or ""
        except Exception:
            text = ""
        if text:
            self.setInputText(text)

    def _write_clipboard(self, text: str) -> bool:
        if self._platform is None:
            return False
        try:
            result = self._platform.clipboard.write_text(text)
        except Exception:
            return False
        return bool(getattr(result, "success", False))

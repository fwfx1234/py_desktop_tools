from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from .service import QrService


class QrViewModel(QObject):
    qrGenerated = Signal(str)
    qrScanFinished = Signal(str, str)
    qrHistoryUpdated = Signal("QVariantList")
    qrHistoryExported = Signal(bool, str)
    inputTextChanged = Signal(str)

    def __init__(self, initial_text: str = "") -> None:
        super().__init__()
        self._service = QrService()
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
    def generateQr(self, content: str) -> None:
        self.qrGenerated.emit(self._service.generate(content))
        self.qrHistoryUpdated.emit(self._service.get_history())

    @Slot(str)
    def scanQrImage(self, imagePath: str) -> None:
        text, error = self._service.scan(imagePath)
        self.qrScanFinished.emit(text, error)
        self.qrHistoryUpdated.emit(self._service.get_history())

    @Slot()
    def clearQrHistory(self) -> None:
        self._service.clear_history()
        self.qrHistoryUpdated.emit(self._service.get_history())

    @Slot(str)
    def exportQrHistory(self, savePath: str) -> None:
        try:
            target = Path(savePath)
            target.parent.mkdir(parents=True, exist_ok=True)
            lines: list[str] = []
            for item in self._service.get_history():
                lines.append(f"[{item.get('type', '')}] {item.get('createdAt', '')}")
                lines.append(str(item.get("content", "")))
                lines.append("")
            target.write_text("\n".join(lines), encoding="utf-8")
            self.qrHistoryExported.emit(True, f"已导出到: {target}")
        except Exception as exc:
            self.qrHistoryExported.emit(False, f"导出失败: {exc}")

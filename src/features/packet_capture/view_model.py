from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from .service import PacketCaptureService


class PacketCaptureViewModel(QObject):
    packetRowsUpdated = Signal("QVariantList")

    def __init__(self) -> None:
        super().__init__()
        self._service = PacketCaptureService(
            on_rows_updated=lambda items: self.packetRowsUpdated.emit(items),
            parent=self,
        )

    @Slot()
    def startPacketCapture(self) -> None:
        self._service.start()

    @Slot()
    def stopPacketCapture(self) -> None:
        self._service.stop()

    @Slot()
    def clearPacketRows(self) -> None:
        self._service.clear_rows()

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from .service import DownloadService


class DownloadViewModel(QObject):
    downloadFinished = Signal(str)
    downloadTaskUpdated = Signal("QVariantList")

    def __init__(self) -> None:
        super().__init__()
        self._disposed = False
        self._service = DownloadService(
            on_tasks_updated=self._emit_tasks_updated,
            on_download_finished=self._emit_download_finished,
        )

    @Slot(str, str)
    def downloadFile(self, url: str, savePath: str) -> None:
        self._service.download_file(url, savePath)

    @Slot()
    def clearDownloadTasks(self) -> None:
        self._service.clear_tasks()

    @Slot(str)
    def cancelDownloadTask(self, taskId: str) -> None:
        self._service.cancel_task(taskId)

    def dispose(self) -> None:
        self._disposed = True
        self._service.close()

    def _emit_tasks_updated(self, items: list[dict]) -> None:
        if not self._disposed:
            self.downloadTaskUpdated.emit(items)

    def _emit_download_finished(self, message: str) -> None:
        if not self._disposed:
            self.downloadFinished.emit(message)

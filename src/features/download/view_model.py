from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from .service import DownloadService


class DownloadViewModel(QObject):
    downloadFinished = Signal(str)
    downloadTaskUpdated = Signal("QVariantList")
    downloadActionResult = Signal(bool, str)
    _uiCallback = Signal(object)

    def __init__(self, platform_api: object | None = None) -> None:
        super().__init__()
        self._disposed = False
        self._platform = platform_api
        self._uiCallback.connect(self._run_ui_callback)
        self._service = DownloadService(
            on_tasks_updated=self._emit_tasks_updated,
            on_download_finished=self._emit_download_finished,
        )

    @Slot(result=str)
    def saveRoot(self) -> str:
        return str(self._service.save_root)

    @Slot(str, str)
    def downloadFile(self, url: str, savePath: str) -> None:
        if not url.strip():
            self.downloadActionResult.emit(False, "URL 为空")
            return
        self._service.download_file(url, savePath)

    @Slot(str)
    def downloadUrl(self, url: str) -> None:
        if not url.strip():
            self.downloadActionResult.emit(False, "URL 为空")
            return
        self._service.download_url(url.strip())

    @Slot()
    def clearDownloadTasks(self) -> None:
        self._service.clear_tasks()

    @Slot()
    def clearCompleted(self) -> None:
        self._service.clear_completed()

    @Slot()
    def clearFailed(self) -> None:
        self._service.clear_failed()

    @Slot(str)
    def cancelDownloadTask(self, taskId: str) -> None:
        self._service.cancel_task(taskId)

    @Slot(str)
    def removeDownloadTask(self, taskId: str) -> None:
        self._service.remove_task(taskId)

    @Slot(str)
    def retryDownloadTask(self, taskId: str) -> None:
        new_id = self._service.retry_task(taskId)
        if not new_id:
            self.downloadActionResult.emit(False, "无法重试该任务")

    @Slot(str)
    def revealDownload(self, taskId: str) -> None:
        task = self._service.get_task(taskId)
        if not task:
            self.downloadActionResult.emit(False, "任务不存在")
            return
        save_path = str(task.get("savePath") or "")
        if not save_path or not Path(save_path).exists():
            self.downloadActionResult.emit(False, "文件未生成或已删除")
            return
        if self._platform is None:
            self.downloadActionResult.emit(False, "平台 API 不可用")
            return
        result = self._platform.reveal_in_file_manager(save_path)
        self.downloadActionResult.emit(
            bool(getattr(result, "success", False)),
            getattr(result, "message", "") or save_path,
        )

    @Slot(str)
    def openDownloadedFile(self, taskId: str) -> None:
        task = self._service.get_task(taskId)
        if not task:
            self.downloadActionResult.emit(False, "任务不存在")
            return
        save_path = str(task.get("savePath") or "")
        if not save_path or not Path(save_path).exists():
            self.downloadActionResult.emit(False, "文件未生成或已删除")
            return
        if self._platform is None:
            self.downloadActionResult.emit(False, "平台 API 不可用")
            return
        result = self._platform.open_path(save_path)
        self.downloadActionResult.emit(
            bool(getattr(result, "success", False)),
            getattr(result, "message", "") or save_path,
        )

    @Slot()
    def revealSaveRoot(self) -> None:
        target = self._service.save_root
        try:
            target.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self.downloadActionResult.emit(False, f"无法访问目录: {exc}")
            return
        if self._platform is None:
            self.downloadActionResult.emit(False, "平台 API 不可用")
            return
        result = self._platform.open_path(target)
        self.downloadActionResult.emit(
            bool(getattr(result, "success", False)),
            getattr(result, "message", "") or str(target),
        )

    @Slot()
    def fillFromClipboard(self) -> str:
        if self._platform is None:
            return ""
        try:
            return self._platform.clipboard.read_text() or ""
        except Exception:
            return ""

    def dispose(self) -> None:
        self._disposed = True
        self._service.close()

    def _emit_tasks_updated(self, items: list[dict]) -> None:
        self._post_ui(lambda payload=list(items): self._emit_tasks_updated_in_ui(payload))

    def _emit_download_finished(self, message: str) -> None:
        self._post_ui(lambda value=str(message): self._emit_download_finished_in_ui(value))

    def _post_ui(self, fn) -> None:
        self._uiCallback.emit(fn)

    @Slot(object)
    def _run_ui_callback(self, fn: object) -> None:
        if not self._disposed and callable(fn):
            fn()

    def _emit_tasks_updated_in_ui(self, items: list[dict]) -> None:
        if not self._disposed:
            self.downloadTaskUpdated.emit(items)

    def _emit_download_finished_in_ui(self, message: str) -> None:
        if not self._disposed:
            self.downloadFinished.emit(message)

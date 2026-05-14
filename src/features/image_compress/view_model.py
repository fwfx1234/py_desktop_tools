from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from app.qt.task_runner import TaskRunner

from .service import ImageCompressService


class ImageCompressViewModel(QObject):
    imageCompressed = Signal(str)
    filesChanged = Signal("QVariantList")

    def __init__(self, initial_files: list[str] | None = None) -> None:
        super().__init__()
        self._service = ImageCompressService()
        self._runner = TaskRunner(self)
        self._initial_files = list(initial_files or [])

    @Slot(result="QVariantList")
    def initialFiles(self) -> list[str]:
        return list(self._initial_files)

    @Slot("QVariantList")
    def setFiles(self, files) -> None:
        next_files = [str(item) for item in files if str(item)]
        if next_files == self._initial_files:
            return
        self._initial_files = next_files
        self.filesChanged.emit(list(self._initial_files))

    @Slot("QVariantList", int, str)
    def compressImages(self, fileUrls, quality: int, mode: str) -> None:
        files = list(fileUrls or [])
        self._runner.start(
            lambda: self._service.compress_images(files, quality, mode),
            on_success=lambda message: self.imageCompressed.emit(str(message or "")),
            on_error=lambda exc: self.imageCompressed.emit(f"压缩失败: {exc}"),
        )

    def dispose(self) -> None:
        self._runner.cancel_all()

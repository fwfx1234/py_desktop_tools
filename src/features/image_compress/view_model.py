from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from app.concurrency import PythonTaskRunner

from .service import ImageCompressService, _normalize_path


class ImageCompressViewModel(QObject):
    resultsUpdated = Signal("QVariantList")
    statusMessage = Signal(str, str)
    _uiCallback = Signal(object)

    def __init__(
        self,
        initial_files: list[str] | None = None,
        platform_api: object | None = None,
        clipboard_service: object | None = None,
    ) -> None:
        super().__init__()
        self._disposed = False
        self._service = ImageCompressService()
        self._runner = PythonTaskRunner(thread_name_prefix="image-compress")
        self._uiCallback.connect(self._run_ui_callback)
        self._platform = platform_api
        self._clipboard_service = clipboard_service
        self._initial_files = list(initial_files or [])

    @Slot(result=str)
    def outputDir(self) -> str:
        return str(self._service.output_dir)

    @Slot(result="QVariantList")
    def initialFiles(self) -> list[str]:
        return list(self._initial_files)

    @Slot("QVariantList", int, str)
    def compressFiles(self, fileUrls, quality: int, mode: str) -> None:
        files = [_normalize_path(str(f)) for f in (fileUrls or []) if str(f)]
        if not files:
            self.statusMessage.emit("未选择任何图片", "error")
            return
        self._runner.start(
            lambda: self._service.compress(files, quality, mode, from_clipboard=False),
            on_success=lambda entries: self._emit_results(entries, label="压缩完成"),
            on_error=lambda exc: self._emit_failure(str(exc)),
        )

    @Slot(int, str)
    def pasteAndCompress(self, quality: int, mode: str) -> None:
        path, from_clipboard, error = self._read_clipboard_image_path()
        if error:
            self.statusMessage.emit(error, "error")
            return
        self._runner.start(
            lambda p=path, c=from_clipboard: self._service.compress([p], quality, mode, from_clipboard=c),
            on_success=lambda entries: self._emit_results(
                entries,
                label="剪贴板图片已压缩" if from_clipboard else "压缩完成",
            ),
            on_error=lambda exc: self._emit_failure(str(exc)),
        )

    @Slot(str, str)
    def saveAs(self, entryId: str, savePath: str) -> None:
        ok, message = self._service.save_as(entryId, savePath)
        self.statusMessage.emit(message, "success" if ok else "error")

    @Slot(str)
    def overwriteOriginal(self, entryId: str) -> None:
        ok, message = self._service.overwrite_original(entryId)
        if ok:
            self._publish_entries()
        self.statusMessage.emit(message, "success" if ok else "error")

    @Slot(str)
    def copyResultToClipboard(self, entryId: str) -> None:
        entry = self._service.get(entryId)
        if entry is None or not entry.success or not entry.output:
            self.statusMessage.emit("无可复制内容", "error")
            return
        if self._clipboard_service is not None and hasattr(self._clipboard_service, "copy_item"):
            try:
                ok = bool(self._clipboard_service.copy_item({
                    "itemType": "image",
                    "content": entry.output,
                }))
            except Exception:
                ok = False
            if ok:
                self.statusMessage.emit("已复制压缩图片到剪贴板", "success")
                return
        if self._platform is not None:
            try:
                result = self._platform.clipboard.write_files([entry.output])
            except Exception:
                result = None
            if result is not None and bool(getattr(result, "success", False)):
                self.statusMessage.emit("已复制压缩图片到剪贴板", "success")
                return
        self.statusMessage.emit("当前平台不支持图片写入剪贴板", "error")

    @Slot(str)
    def revealOutput(self, entryId: str) -> None:
        entry = self._service.get(entryId)
        if entry is None or not entry.output:
            self.statusMessage.emit("无输出文件", "error")
            return
        if self._platform is None:
            self.statusMessage.emit("平台 API 不可用", "error")
            return
        result = self._platform.reveal_in_file_manager(entry.output)
        ok = bool(getattr(result, "success", False))
        self.statusMessage.emit(
            getattr(result, "message", "") or entry.output if not ok else f"已定位 {entry.output}",
            "success" if ok else "error",
        )

    @Slot(str)
    def removeResult(self, entryId: str) -> None:
        self._service.remove(entryId)
        self._publish_entries()

    @Slot()
    def clearResults(self) -> None:
        self._service.clear()
        self._publish_entries()

    def dispose(self) -> None:
        self._disposed = True
        self._runner.shutdown(wait=False)

    def _read_clipboard_image_path(self) -> tuple[str, bool, str]:
        """Return (path, from_clipboard, error).

        from_clipboard=True means the image came from in-memory clipboard
        without a user-owned source file (overwrite-original must be blocked).
        from_clipboard=False means the clipboard pointed at a real file on
        disk (e.g. user copied a file from Finder); overwrite is allowed.
        """
        service = self._clipboard_service
        if service is None:
            return "", False, "剪贴板服务不可用"
        item = None
        for attr in ("latest_context_item", "latest_captured_item", "latest_item"):
            getter = getattr(service, attr, None)
            if callable(getter):
                try:
                    item = getter()
                except Exception:
                    item = None
                if item:
                    break
        if not isinstance(item, dict):
            return "", False, "剪贴板中没有图片，请先复制一张图片"
        item_type = str(item.get("itemType") or "")
        if item_type == "image":
            path = str(item.get("content") or "")
            if not path:
                return "", True, "无法读取剪贴板图片路径"
            return path, True, ""
        if item_type == "files":
            metadata = item.get("metadata") or {}
            paths = metadata.get("paths") if isinstance(metadata, dict) else None
            candidates: list[str] = []
            if isinstance(paths, list):
                candidates = [str(p) for p in paths if p]
            if not candidates:
                content = str(item.get("content") or "")
                candidates = [p.strip() for p in content.split(",") if p.strip()]
            for candidate in candidates:
                lowered = candidate.lower()
                if lowered.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")):
                    return candidate, False, ""
            return "", False, "剪贴板中没有图片，请先复制一张图片"
        return "", False, "剪贴板中没有图片，请先复制一张图片"

    def _emit_results(self, entries, *, label: str) -> None:
        success = sum(1 for e in entries if e.success)
        failed = sum(1 for e in entries if not e.success)
        message = f"{label}：成功 {success} / 失败 {failed}"
        self._post_ui(lambda: self._publish_entries())
        self._post_ui(lambda: self._emit_status_in_ui(message, "success" if failed == 0 else "error"))

    def _emit_failure(self, error: str) -> None:
        self._post_ui(lambda: self._emit_status_in_ui(f"压缩失败: {error}", "error"))

    def _publish_entries(self) -> None:
        payload = [entry.to_dict() for entry in self._service.entries()]
        self._post_ui(lambda data=payload: self._emit_results_in_ui(data))

    def _post_ui(self, fn) -> None:
        self._uiCallback.emit(fn)

    @Slot(object)
    def _run_ui_callback(self, fn: object) -> None:
        if not self._disposed and callable(fn):
            fn()

    def _emit_results_in_ui(self, entries) -> None:
        if not self._disposed:
            self.resultsUpdated.emit(entries)

    def _emit_status_in_ui(self, message: str, kind: str) -> None:
        if not self._disposed:
            self.statusMessage.emit(message, kind)

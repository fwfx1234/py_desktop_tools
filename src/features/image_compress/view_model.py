from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from app.concurrency import PythonTaskRunner

from .service import ImageCompressService, _normalize_path


class ImageCompressViewModel(QObject):
    entriesUpdated = Signal("QVariantList")
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
        if initial_files:
            self._service.add_pending(initial_files, from_clipboard=False)

    @Slot(result=str)
    def outputDir(self) -> str:
        return str(self._service.output_dir)

    @Slot(result="QVariantList")
    def currentEntries(self) -> list[dict]:
        return [entry.to_dict() for entry in self._service.entries()]

    @Slot()
    def emitInitial(self) -> None:
        self._publish_entries()

    @Slot("QVariantList")
    def addFiles(self, fileUrls) -> None:
        files = [_normalize_path(str(f)) for f in (fileUrls or []) if str(f)]
        if not files:
            self.statusMessage.emit("未选择任何图片", "error")
            return
        self._service.add_pending(files, from_clipboard=False)
        self._publish_entries()
        self.statusMessage.emit(f"已加入 {len(files)} 张，点击「开始压缩」", "info")

    @Slot()
    def pasteClipboard(self) -> None:
        path, from_clipboard, error = self._read_clipboard_image()
        if error:
            self.statusMessage.emit(error, "error")
            return
        self._service.add_pending([path], from_clipboard=from_clipboard)
        self._publish_entries()
        if from_clipboard:
            self.statusMessage.emit("已读取剪贴板图片，点击「开始压缩」", "info")
        else:
            self.statusMessage.emit("已加入剪贴板中的文件，点击「开始压缩」", "info")

    @Slot(int, str)
    def startCompression(self, quality: int, mode: str) -> None:
        if not self._service.pending_ids():
            self.statusMessage.emit("没有待压缩的图片", "error")
            return
        self._runner.start(
            lambda: self._service.compress_pending(quality, mode),
            on_success=lambda entries: self._emit_after_compress(entries),
            on_error=lambda exc: self._post_status(f"压缩失败: {exc}", "error"),
        )

    @Slot(str, int, str)
    def retryEntry(self, entryId: str, quality: int, mode: str) -> None:
        self._runner.start(
            lambda: self._service.retry(entryId, quality, mode),
            on_success=lambda _entry: self._emit_after_compress(self._service.entries()),
            on_error=lambda exc: self._post_status(f"重试失败: {exc}", "error"),
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
        copied = False
        if self._clipboard_service is not None and hasattr(self._clipboard_service, "copy_item"):
            try:
                copied = bool(self._clipboard_service.copy_item({
                    "itemType": "image",
                    "content": entry.output,
                }))
            except Exception:
                copied = False
        if not copied and self._platform is not None:
            try:
                result = self._platform.clipboard.write_files([entry.output])
            except Exception:
                result = None
            copied = bool(result and getattr(result, "success", False))
        if copied:
            self.statusMessage.emit("已复制压缩图片到剪贴板", "success")
        else:
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
            f"已定位 {entry.output}" if ok else (getattr(result, "message", "") or entry.output),
            "success" if ok else "error",
        )

    @Slot(str)
    def removeEntry(self, entryId: str) -> None:
        self._service.remove(entryId)
        self._publish_entries()

    @Slot()
    def clearAll(self) -> None:
        self._service.clear()
        self._publish_entries()

    def dispose(self) -> None:
        self._disposed = True
        self._runner.shutdown(wait=False)

    def _read_clipboard_image(self) -> tuple[str, bool, str]:
        """Return (path, from_clipboard, error).

        ``from_clipboard=True`` 表示截图等无源图片（必须禁用「覆盖原图」）;
        ``from_clipboard=False`` 表示剪贴板里是真实文件路径（允许覆盖原图）。
        """
        service = self._clipboard_service
        if service is None:
            return "", False, "剪贴板服务不可用"
        item = None
        # 1) 优先读取实时 pasteboard，避免监听器还没来得及捕获
        live_getter = getattr(service, "read_live_item", None)
        if callable(live_getter):
            try:
                item = live_getter()
            except Exception:
                item = None
        # 2) fallback：历史记录里最近一条
        if not item:
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
                if candidate.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")):
                    return candidate, False, ""
            return "", False, "剪贴板中没有图片，请先复制一张图片"
        return "", False, "剪贴板中没有图片，请先复制一张图片"

    def _emit_after_compress(self, entries) -> None:
        success = sum(1 for e in entries if e.state == "success")
        failed = sum(1 for e in entries if e.state == "failed")
        message = f"压缩完成：成功 {success} / 失败 {failed}"
        self._post_ui(lambda: self._publish_entries())
        self._post_ui(lambda: self._emit_status_in_ui(message, "success" if failed == 0 else "error"))

    def _post_status(self, message: str, kind: str) -> None:
        self._post_ui(lambda m=message, k=kind: self._emit_status_in_ui(m, k))

    def _publish_entries(self) -> None:
        payload = [entry.to_dict() for entry in self._service.entries()]
        self._post_ui(lambda data=payload: self._emit_entries_in_ui(data))

    def _post_ui(self, fn) -> None:
        self._uiCallback.emit(fn)

    @Slot(object)
    def _run_ui_callback(self, fn: object) -> None:
        if not self._disposed and callable(fn):
            fn()

    def _emit_entries_in_ui(self, entries) -> None:
        if not self._disposed:
            self.entriesUpdated.emit(entries)

    def _emit_status_in_ui(self, message: str, kind: str) -> None:
        if not self._disposed:
            self.statusMessage.emit(message, kind)

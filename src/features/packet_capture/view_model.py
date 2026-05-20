from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from .service import CaptureState, FlowSummary, PacketCaptureService, filter_rows


class PacketCaptureViewModel(QObject):
    packetStateUpdated = Signal("QVariantMap")
    packetRowsUpdated = Signal("QVariantList")
    packetDetailUpdated = Signal("QVariantMap")
    packetActionResult = Signal(bool, str)
    _uiCallback = Signal(object)

    def __init__(self, platform_api: object | None = None) -> None:
        super().__init__()
        self._disposed = False
        self._platform = platform_api
        self._uiCallback.connect(self._run_ui_callback)
        self._service = PacketCaptureService(
            on_state_changed=self._on_state_changed,
            on_flow_event=self._on_flow_event,
        )
        self._filter_keyword = ""
        self._filter_method = ""
        self._filter_content_type = ""
        self._filter_status_min = 0
        self._filter_status_max = 0
        self._filter_only_errors = False
        # initial push
        self._emit_state(self._service.state)

    @Slot(result="QVariantMap")
    def initialState(self) -> dict:
        return self._service.state.to_dict()

    @Slot()
    def startPacketCapture(self) -> None:
        self._service.start()

    @Slot()
    def stopPacketCapture(self) -> None:
        self._service.stop()

    @Slot()
    def pausePacketCapture(self) -> None:
        self._service.pause()

    @Slot()
    def resumePacketCapture(self) -> None:
        self._service.resume()

    @Slot()
    def clearPacketRows(self) -> None:
        self._service.clear()
        self._publish_rows()

    @Slot(str)
    def selectFlow(self, flowId: str) -> None:
        detail = self._service.detail(flowId)
        if detail is None:
            self.packetDetailUpdated.emit({})
        else:
            self.packetDetailUpdated.emit(detail.to_dict())

    @Slot(str)
    def copyCurl(self, flowId: str) -> None:
        text = self._service.build_curl(flowId)
        if not text:
            self.packetActionResult.emit(False, "无可复制内容")
            return
        ok = self._write_clipboard(text)
        self.packetActionResult.emit(ok, "已复制 cURL" if ok else "复制失败")

    @Slot(str)
    def copyUrl(self, flowId: str) -> None:
        text = self._service.request_url(flowId)
        if not text:
            self.packetActionResult.emit(False, "无可复制 URL")
            return
        ok = self._write_clipboard(text)
        self.packetActionResult.emit(ok, "已复制 URL" if ok else "复制失败")

    @Slot()
    def revealCertDir(self) -> None:
        target = self._service.cert_directory()
        try:
            target.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self.packetActionResult.emit(False, f"无法访问目录: {exc}")
            return
        if self._platform is None:
            self.packetActionResult.emit(False, "平台 API 不可用")
            return
        result = self._platform.open_path(target)
        self.packetActionResult.emit(
            bool(getattr(result, "success", False)),
            getattr(result, "message", "") or str(target),
        )

    @Slot()
    def copyProxyAddress(self) -> None:
        state = self._service.state
        if not state.proxy_url:
            self.packetActionResult.emit(False, "代理未启动")
            return
        ok = self._write_clipboard(state.proxy_url)
        self.packetActionResult.emit(ok, state.proxy_url if ok else "复制失败")

    @Slot(str, str)
    def saveResponseBody(self, flowId: str, savePath: str) -> None:
        if not savePath:
            self.packetActionResult.emit(False, "未提供保存路径")
            return
        cleaned = savePath
        if cleaned.startswith("file://"):
            cleaned = cleaned.replace("file://", "", 1)
        target = Path(cleaned)
        ok, message = self._service.save_response_body(flowId, target)
        self.packetActionResult.emit(ok, message)

    @Slot(str, str, str, int, int, bool)
    def setFilters(
        self,
        keyword: str,
        method: str,
        contentType: str,
        statusMin: int,
        statusMax: int,
        onlyErrors: bool,
    ) -> None:
        self._filter_keyword = keyword or ""
        self._filter_method = method or ""
        self._filter_content_type = contentType or ""
        self._filter_status_min = int(statusMin or 0)
        self._filter_status_max = int(statusMax or 0)
        self._filter_only_errors = bool(onlyErrors)
        self._publish_rows()

    def dispose(self) -> None:
        self._disposed = True
        try:
            self._service.stop()
        except Exception:
            pass

    def _publish_rows(self) -> None:
        rows = self._service.rows()
        filtered = filter_rows(
            rows,
            keyword=self._filter_keyword,
            method=self._filter_method,
            status_min=self._filter_status_min,
            status_max=self._filter_status_max,
            content_type=self._filter_content_type,
            only_errors=self._filter_only_errors,
        )
        payload = [row.to_dict() for row in filtered]
        self._post_ui(lambda data=payload: self._emit_rows_in_ui(data))

    def _on_state_changed(self, state: CaptureState) -> None:
        self._emit_state(state)

    def _on_flow_event(self, kind: str, summary: FlowSummary) -> None:
        del kind, summary
        self._publish_rows()

    def _emit_state(self, state: CaptureState) -> None:
        snapshot = state.to_dict()
        self._post_ui(lambda data=snapshot: self._emit_state_in_ui(data))

    def _write_clipboard(self, text: str) -> bool:
        if self._platform is None:
            return False
        try:
            result = self._platform.clipboard.write_text(text)
        except Exception:
            return False
        return bool(getattr(result, "success", False))

    def _post_ui(self, fn) -> None:
        self._uiCallback.emit(fn)

    @Slot(object)
    def _run_ui_callback(self, fn: object) -> None:
        if not self._disposed and callable(fn):
            fn()

    def _emit_state_in_ui(self, payload: dict) -> None:
        if not self._disposed:
            self.packetStateUpdated.emit(payload)

    def _emit_rows_in_ui(self, rows: list) -> None:
        if not self._disposed:
            self.packetRowsUpdated.emit(rows)

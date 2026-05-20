from __future__ import annotations

from collections.abc import Callable
from threading import Lock
from urllib.parse import urlencode
from uuid import uuid4

from app.concurrency import PythonTaskRunner
from app.logging import get_logger

from .service import ApiTestService

ResponseCallback = Callable[[str, str, dict], None]
HistoryCallback = Callable[[list[dict]], None]
SendingCallback = Callable[[bool], None]
WsTimelineCallback = Callable[[str], None]
WsStatusCallback = Callable[[str, str, str], None]


class RequestSenderCoordinator:
    def __init__(
        self,
        service: ApiTestService,
        *,
        on_response: ResponseCallback,
        on_history: HistoryCallback,
        on_sending: SendingCallback,
        on_ws_timeline: WsTimelineCallback | None = None,
        on_ws_status: WsStatusCallback | None = None,
        task_runner: PythonTaskRunner | None = None,
    ) -> None:
        self._service = service
        self._on_response = on_response
        self._on_history = on_history
        self._on_sending = on_sending
        self._on_ws_timeline = on_ws_timeline
        self._on_ws_status = on_ws_status
        self._runner = task_runner or PythonTaskRunner(thread_name_prefix="api-test")
        self._sending = False
        self._active_request_id = ""
        self._disposed = False
        self._lock = Lock()
        self._log = get_logger("features.api_test.request_sender", plugin_id="api-test")

    def send_request(self, data: dict) -> None:
        method = str(data.get("method") or "GET")
        url = str(data.get("url") or "")
        params_text = str(data.get("paramsText") or "")
        headers_text = str(data.get("headersText") or "")
        body_text = str(data.get("bodyText") or "")
        env_base_url = str(data.get("envBaseUrl") or "")
        auth_type = str(data.get("authType") or "none")
        auth_value = str(data.get("authValue") or "")
        mock_mode = bool(data.get("mockMode"))
        request_mode = str(data.get("requestMode") or "http")
        tab_id = str(data.get("tabId") or "")
        file_path = str(data.get("filePath") or "")
        file_param = str(data.get("fileParamName") or "file")
        cookies_text = str(data.get("cookiesText") or "")
        current_body_mode = int(data.get("currentBodyMode") or 0)
        body_form_rows = data.get("bodyFormRows") or []
        ws_encoding = str(data.get("wsEncoding") or "text")
        pre_ops = str(data.get("preOpsText") or "")
        post_ops = str(data.get("postOpsText") or "")

        if request_mode == "websocket" and not mock_mode:
            self.send_ws(tab_id, body_text, ws_encoding)
            return
        if current_body_mode == 1:
            if not mock_mode:
                headers_text = self._ensure_header(headers_text, "Content-Type", "application/x-www-form-urlencoded")
        elif current_body_mode == 2 and not mock_mode:
            headers_text = self._ensure_header(headers_text, "Content-Type", "application/json")
        elif current_body_mode == 3 and not mock_mode:
            headers_text = self._ensure_header(headers_text, "Content-Type", "application/xml")
        elif current_body_mode == 4 and body_text and not mock_mode:
            headers_text = self._ensure_header(headers_text, "Content-Type", "text/plain")
        if cookies_text.strip():
            if headers_text:
                headers_text += "\n"
            headers_text += f"Cookie: {cookies_text.strip()}"
        if current_body_mode == 1:
            body_text = self._build_form_body(body_form_rows)
        if current_body_mode == 5:
            self.send_api_file(
                method,
                url,
                params_text,
                headers_text,
                file_path,
                file_param,
                env_base_url,
                auth_type,
                auth_value,
                pre_ops,
                post_ops,
                tab_id,
            )
            return
        mock_response = body_text if mock_mode else ""
        self.send_api(
            method,
            url,
            params_text,
            headers_text,
            body_text,
            env_base_url,
            auth_type,
            auth_value,
            request_mode,
            "",
            "",
            pre_ops,
            post_ops,
            mock_response,
            tab_id,
            body_form_rows if current_body_mode == 1 else None,
        )

    def send_api_file(
        self,
        method,
        url,
        params_text,
        headers_text,
        file_path,
        file_param,
        env_base_url,
        auth_type,
        auth_value,
        global_params_text,
        assertions_text,
        tab_id,
    ) -> None:
        request_id = self._begin_request()
        if not request_id:
            return
        self._log.info(
            "api.request.start",
            "开始发送文件请求",
            requestId=request_id,
            method=str(method),
            urlLength=len(str(url or "")),
            tabId=str(tab_id or ""),
        )

        def run_request() -> tuple[str, str, dict]:
            return self._service.send_api_file(
                method,
                url,
                params_text,
                headers_text,
                file_path,
                file_param,
                env_base_url,
                auth_type,
                auth_value,
                global_params_text,
                assertions_text,
                tab_id,
            )

        self._runner.start(
            run_request,
            on_success=lambda result: self._handle_request_success(request_id, result),
            on_error=lambda exc: self._handle_request_error(request_id, exc),
            on_done=lambda: self._finish_request(request_id),
        )

    def send_api(
        self,
        method,
        url,
        params_text,
        headers_text,
        body_text,
        env_base_url,
        auth_type,
        auth_value,
        request_mode,
        graphql_query,
        graphql_variables,
        global_params_text,
        assertions_text,
        mock_response_text,
        tab_id,
        body_form_rows=None,
    ) -> None:
        request_id = self._begin_request()
        if not request_id:
            return
        self._log.info(
            "api.request.start",
            "开始发送请求",
            requestId=request_id,
            method=str(method),
            mode=str(request_mode),
            urlLength=len(str(url or "")),
            bodyLength=len(str(body_text or "")),
            tabId=str(tab_id or ""),
        )

        def run_request() -> tuple[str, str, dict]:
            return self._service.send_api(
                method,
                url,
                params_text,
                headers_text,
                body_text,
                env_base_url,
                auth_type,
                auth_value,
                request_mode,
                graphql_query,
                graphql_variables,
                global_params_text,
                assertions_text,
                mock_response_text,
                tab_id,
                body_form_rows,
            )

        self._runner.start(
            run_request,
            on_success=lambda result: self._handle_request_success(request_id, result),
            on_error=lambda exc: self._handle_request_error(request_id, exc),
            on_done=lambda: self._finish_request(request_id),
        )

    def connect_ws(self, tab_id: str, url: str, params_text: str, headers_text: str, cookies_text: str, env_base_url: str) -> None:
        self._emit_ws_status(tab_id, "connecting", "正在连接")
        self._run_ws_task(tab_id, lambda: self._service.ws_connect(tab_id, url, params_text, headers_text, cookies_text, env_base_url))

    def send_ws(self, tab_id: str, content: str, encoding: str) -> None:
        self._run_ws_task(tab_id, lambda: self._service.ws_send(tab_id, content, encoding))

    def receive_ws(self, tab_id: str) -> None:
        self._emit_ws_status(tab_id, "receiving", "正在接收")
        self._run_ws_task(tab_id, lambda: self._service.ws_receive(tab_id))

    def disconnect_ws(self, tab_id: str) -> None:
        self._emit_ws_status(tab_id, "disconnecting", "正在断开")
        self._run_ws_task(tab_id, lambda: self._service.ws_disconnect(tab_id))

    def send_ws_message(self, tab_id: str, content: str, encoding: str) -> None:
        self.send_ws(tab_id, content, encoding)

    def dispose(self) -> None:
        with self._lock:
            self._disposed = True
            self._active_request_id = ""
            self._sending = False
        self._runner.shutdown(wait=False)

    def _begin_request(self) -> str:
        busy = False
        request_id = ""
        with self._lock:
            if self._disposed:
                return ""
            if self._sending:
                busy = True
            else:
                self._sending = True
                self._active_request_id = uuid4().hex
                request_id = self._active_request_id
        if busy:
            self._on_response("状态: BUSY", "已有请求正在发送中，请稍后再试。", {})
            return ""
        self._on_sending(True)
        return request_id

    def _request_is_current(self, request_id: str) -> bool:
        with self._lock:
            return not self._disposed and self._active_request_id == request_id

    def _finish_request(self, request_id: str) -> None:
        should_emit = False
        with self._lock:
            if self._active_request_id != request_id:
                return
            self._sending = False
            self._active_request_id = ""
            if self._disposed:
                return
            should_emit = True
        if should_emit:
            self._on_sending(False)

    def _handle_request_success(self, request_id: str, result: object) -> None:
        title, body, details = result if isinstance(result, tuple) and len(result) == 3 else ("状态: ERR", "请求结果格式异常。", {})
        status_code = ""
        if isinstance(details, dict):
            status_code = str(details.get("statusCode") or "")
        self._log.info("api.request.complete", "请求完成", requestId=request_id, statusCode=status_code)
        self._emit_response_if_current(request_id, str(title), str(body), dict(details or {}))

    def _handle_request_error(self, request_id: str, exc: BaseException) -> None:
        self._log.warning("api.request.failed", "请求失败", requestId=request_id, error=str(exc))
        self._emit_response_if_current(request_id, "状态: ERR", str(exc), {})

    def _emit_response_if_current(self, request_id: str, title: str, body: str, details: dict) -> None:
        if not self._request_is_current(request_id):
            return
        response_details = dict(details or {})
        response_details["requestId"] = request_id
        self._on_response(title, body, response_details)
        self._on_history(self._service.list_history())

    def _run_ws_task(self, tab_id: str, fn: Callable[[], tuple[str, str]]) -> None:
        if self._is_disposed():
            return

        def on_success(result: object) -> None:
            if self._is_disposed():
                return
            title, body = result if isinstance(result, tuple) and len(result) == 2 else ("状态: WS_ERR", "WebSocket 返回结果格式异常。")
            self._on_response(str(title), str(body), {})
            self._emit_ws_status(tab_id, self._ws_status_from_title(str(title), tab_id), str(body))
            if self._on_ws_timeline:
                self._on_ws_timeline(tab_id)

        def on_error(exc: BaseException) -> None:
            if self._is_disposed():
                return
            self._log.warning("api.websocket.failed", "WebSocket 操作失败", tabId=tab_id, error=str(exc))
            self._on_response("状态: WS_ERR", str(exc), {})
            self._emit_ws_status(tab_id, "error", str(exc))

        self._runner.start(fn, on_success=on_success, on_error=on_error)

    def _is_disposed(self) -> bool:
        with self._lock:
            return self._disposed

    def _emit_ws_status(self, tab_id: str, status: str, message: str) -> None:
        if self._on_ws_status:
            self._on_ws_status(tab_id, status, message)

    def _ws_status_from_title(self, title: str, tab_id: str) -> str:
        if "WS_CONNECTED" in title:
            return "connected"
        if "WS_DISCONNECTED" in title:
            return "disconnected"
        if self._service.ws_connected(tab_id):
            return "connected"
        return "disconnected"

    @staticmethod
    def _build_form_body(rows: object) -> str:
        pairs: list[tuple[str, str]] = []
        if not isinstance(rows, list):
            return ""
        for row in rows:
            if not isinstance(row, dict) or row.get("enabled") is False:
                continue
            key = str(row.get("key") or "")
            if key:
                pairs.append((key, str(row.get("value") or "")))
        return urlencode(pairs)

    @classmethod
    def _ensure_header(cls, headers_text: str, key: str, value: str) -> str:
        if cls._has_header(headers_text, key):
            return headers_text
        if headers_text:
            return f"{headers_text}\n{key}: {value}"
        return f"{key}: {value}"

    @staticmethod
    def _has_header(headers_text: str, key: str) -> bool:
        target = key.strip().lower()
        for line in (headers_text or "").splitlines():
            if ":" not in line:
                continue
            header_key = line.split(":", 1)[0].strip().lower()
            if header_key == target:
                return True
        return False

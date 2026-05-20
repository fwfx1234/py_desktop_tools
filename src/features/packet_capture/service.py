from __future__ import annotations

import asyncio
import socket
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urlsplit

DEFAULT_LISTEN_HOST = "127.0.0.1"
DEFAULT_LISTEN_PORT = 8899
DEFAULT_PORT_TRY = 8
CERT_DIRECTORY = Path.home() / ".mitmproxy"
CERT_FILE = CERT_DIRECTORY / "mitmproxy-ca-cert.pem"


@dataclass(slots=True)
class CaptureState:
    running: bool = False
    paused: bool = False
    listen_host: str = DEFAULT_LISTEN_HOST
    listen_port: int = 0
    cert_path: str = ""
    cert_exists: bool = False
    proxy_url: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "running": self.running,
            "paused": self.paused,
            "listenHost": self.listen_host,
            "listenPort": self.listen_port,
            "certPath": self.cert_path,
            "certExists": self.cert_exists,
            "certDir": str(CERT_DIRECTORY),
            "proxyUrl": self.proxy_url,
            "error": self.error,
        }


@dataclass(slots=True)
class FlowSummary:
    id: str
    method: str
    scheme: str
    host: str
    path: str
    status: int
    content_type: str
    size: int
    duration_ms: int
    started_at: str
    encrypted: bool = False
    error: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "method": self.method,
            "scheme": self.scheme,
            "host": self.host,
            "path": self.path,
            "status": self.status,
            "contentType": self.content_type,
            "size": self.size,
            "durationMs": self.duration_ms,
            "startedAt": self.started_at,
            "encrypted": self.encrypted,
            "error": self.error,
            "note": self.note,
        }


@dataclass(slots=True)
class FlowDetail:
    id: str
    request_url: str
    request_method: str
    request_headers: list[tuple[str, str]] = field(default_factory=list)
    request_body: str = ""
    request_body_truncated: bool = False
    response_status: int = 0
    response_reason: str = ""
    response_headers: list[tuple[str, str]] = field(default_factory=list)
    response_body: str = ""
    response_body_truncated: bool = False
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "requestUrl": self.request_url,
            "requestMethod": self.request_method,
            "requestHeaders": [{"name": k, "value": v} for k, v in self.request_headers],
            "requestBody": self.request_body,
            "requestBodyTruncated": self.request_body_truncated,
            "responseStatus": self.response_status,
            "responseReason": self.response_reason,
            "responseHeaders": [{"name": k, "value": v} for k, v in self.response_headers],
            "responseBody": self.response_body,
            "responseBodyTruncated": self.response_body_truncated,
            "note": self.note,
        }


MAX_BODY_BYTES = 64 * 1024
MAX_ROWS = 500


def find_free_port(host: str, start: int, attempts: int = DEFAULT_PORT_TRY) -> int:
    last_error: Exception | None = None
    for offset in range(max(1, attempts)):
        candidate = start + offset
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((host, candidate))
                return candidate
        except OSError as exc:
            last_error = exc
            continue
    raise OSError(f"无可用端口（起始 {start}）: {last_error}")


def summarize_flow(flow_obj) -> FlowSummary:
    request = getattr(flow_obj, "request", None)
    response = getattr(flow_obj, "response", None)
    method = getattr(request, "method", "") if request else ""
    scheme = getattr(request, "scheme", "") if request else ""
    host = getattr(request, "host", "") if request else ""
    path = getattr(request, "path", "") if request else ""
    pretty_url = getattr(request, "pretty_url", "") if request else ""
    if not host and pretty_url:
        try:
            host = urlsplit(pretty_url).hostname or ""
        except Exception:
            host = ""
    status = int(getattr(response, "status_code", 0) or 0) if response else 0
    headers = getattr(response, "headers", None) if response else None
    content_type = ""
    if headers is not None:
        for key in ("content-type", "Content-Type"):
            value = headers.get(key) if hasattr(headers, "get") else None
            if value:
                content_type = value.split(";")[0].strip()
                break
    size = 0
    if response is not None:
        raw = getattr(response, "raw_content", None) or b""
        size = len(raw)
    error = ""
    if getattr(flow_obj, "error", None) is not None:
        error = str(getattr(flow_obj.error, "msg", flow_obj.error))
    timestamp_start = getattr(request, "timestamp_start", None) if request else None
    timestamp_end = getattr(response, "timestamp_end", None) if response else None
    duration_ms = 0
    started_at = ""
    if timestamp_start is not None:
        started_at = time.strftime("%H:%M:%S", time.localtime(float(timestamp_start)))
        if timestamp_end is not None:
            duration_ms = int(max(0, (float(timestamp_end) - float(timestamp_start)) * 1000))
    encrypted = bool(getattr(request, "url", "").startswith("https://")) if request else False
    flow_id = getattr(flow_obj, "id", "") or f"flow-{int(time.time() * 1000)}"
    return FlowSummary(
        id=flow_id,
        method=method,
        scheme=scheme,
        host=host,
        path=path,
        status=status,
        content_type=content_type,
        size=size,
        duration_ms=duration_ms,
        started_at=started_at,
        encrypted=encrypted,
        error=error,
    )


def flow_detail(flow_obj) -> FlowDetail:
    request = getattr(flow_obj, "request", None)
    response = getattr(flow_obj, "response", None)
    detail = FlowDetail(
        id=getattr(flow_obj, "id", ""),
        request_url=getattr(request, "pretty_url", "") if request else "",
        request_method=getattr(request, "method", "") if request else "",
    )
    if request is not None:
        detail.request_headers = _headers_list(request.headers)
        raw = getattr(request, "raw_content", None) or b""
        body, truncated = _decode_body(raw, request.headers)
        detail.request_body = body
        detail.request_body_truncated = truncated
    if response is not None:
        detail.response_status = int(getattr(response, "status_code", 0) or 0)
        detail.response_reason = getattr(response, "reason", "") or ""
        detail.response_headers = _headers_list(response.headers)
        raw = getattr(response, "raw_content", None) or b""
        body, truncated = _decode_body(raw, response.headers)
        detail.response_body = body
        detail.response_body_truncated = truncated
    return detail


def _headers_list(headers) -> list[tuple[str, str]]:
    if headers is None:
        return []
    try:
        return [(str(name), str(value)) for name, value in headers.items()]
    except Exception:
        return []


def _decode_body(raw: bytes, headers) -> tuple[str, bool]:
    if not raw:
        return "", False
    truncated = False
    payload = raw
    if len(raw) > MAX_BODY_BYTES:
        payload = raw[:MAX_BODY_BYTES]
        truncated = True
    encoding = "utf-8"
    if headers is not None:
        ctype = headers.get("content-type") if hasattr(headers, "get") else None
        if ctype:
            parts = [p.strip() for p in ctype.split(";")]
            for part in parts:
                if part.lower().startswith("charset="):
                    encoding = part.split("=", 1)[1].strip().strip("\"' ") or "utf-8"
    try:
        return payload.decode(encoding, errors="replace"), truncated
    except Exception:
        return payload.decode("utf-8", errors="replace"), truncated


class PacketCaptureService:
    def __init__(
        self,
        on_state_changed: Callable[[CaptureState], None],
        on_flow_event: Callable[[str, FlowSummary], None],
    ) -> None:
        self._on_state_changed = on_state_changed
        self._on_flow_event = on_flow_event
        self._state = CaptureState(cert_path=str(CERT_FILE), cert_exists=CERT_FILE.exists())
        self._flows: dict[str, object] = {}
        self._rows: list[FlowSummary] = []
        self._lock = threading.Lock()
        self._master = None
        self._loop = None
        self._thread: threading.Thread | None = None
        self._started_event = threading.Event()
        self._start_error: str | None = None

    @property
    def state(self) -> CaptureState:
        return self._state

    def cert_directory(self) -> Path:
        return CERT_DIRECTORY

    def cert_path(self) -> Path:
        return CERT_FILE

    def start(self, host: str = DEFAULT_LISTEN_HOST, start_port: int = DEFAULT_LISTEN_PORT) -> CaptureState:
        if self._state.running:
            return self._state
        try:
            port = find_free_port(host, start_port)
        except Exception as exc:
            self._state.error = f"无可用端口: {exc}"
            self._emit_state()
            return self._state

        from mitmproxy import options
        from mitmproxy.tools.dump import DumpMaster
        from mitmproxy.addons.errorcheck import ErrorCheck

        self._started_event.clear()
        self._start_error = None

        def runner() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            try:
                opts = options.Options(
                    listen_host=host,
                    listen_port=port,
                    ssl_insecure=True,
                )
                master = DumpMaster(opts, with_termlog=False, with_dumper=False)
                addon = _CollectorAddon(self)
                try:
                    master.addons.remove(master.addons.get("errorcheck"))
                except Exception:
                    pass
                master.addons.add(addon)
                self._master = master
                self._started_event.set()
                loop.run_until_complete(master.run())
            except Exception as exc:
                self._start_error = str(exc)
                self._started_event.set()
            finally:
                try:
                    loop.close()
                except Exception:
                    pass
                self._loop = None
                self._master = None
                self._state.running = False
                self._state.paused = False
                self._emit_state()

        self._thread = threading.Thread(target=runner, name="packet-capture-proxy", daemon=True)
        self._thread.start()
        if not self._started_event.wait(timeout=5.0):
            self._state.error = "代理启动超时"
            self._emit_state()
            return self._state
        if self._start_error:
            self._state.error = self._start_error
            self._emit_state()
            return self._state

        self._state.running = True
        self._state.paused = False
        self._state.listen_host = host
        self._state.listen_port = port
        self._state.proxy_url = f"http://{host}:{port}"
        self._state.cert_exists = CERT_FILE.exists()
        self._state.error = ""
        self._emit_state()
        return self._state

    def stop(self) -> CaptureState:
        master = self._master
        loop = self._loop
        if master is not None and loop is not None:
            try:
                loop.call_soon_threadsafe(master.shutdown)
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        self._state.running = False
        self._state.paused = False
        self._emit_state()
        return self._state

    def pause(self) -> CaptureState:
        if self._state.running:
            self._state.paused = True
            self._emit_state()
        return self._state

    def resume(self) -> CaptureState:
        if self._state.running:
            self._state.paused = False
            self._emit_state()
        return self._state

    def clear(self) -> list[FlowSummary]:
        with self._lock:
            self._rows = []
            self._flows.clear()
        return []

    def rows(self) -> list[FlowSummary]:
        with self._lock:
            return list(self._rows)

    def detail(self, flow_id: str) -> FlowDetail | None:
        with self._lock:
            flow_obj = self._flows.get(flow_id)
        if flow_obj is None:
            return None
        return flow_detail(flow_obj)

    def save_response_body(self, flow_id: str, target: Path) -> tuple[bool, str]:
        with self._lock:
            flow_obj = self._flows.get(flow_id)
        if flow_obj is None or getattr(flow_obj, "response", None) is None:
            return False, "未找到响应正文"
        raw = getattr(flow_obj.response, "raw_content", None) or b""
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        except Exception as exc:
            return False, f"保存失败: {exc}"
        return True, str(target)

    def build_curl(self, flow_id: str) -> str:
        with self._lock:
            flow_obj = self._flows.get(flow_id)
        if flow_obj is None or getattr(flow_obj, "request", None) is None:
            return ""
        request = flow_obj.request
        parts = ["curl", "-X", request.method]
        for name, value in _headers_list(request.headers):
            parts.append(f"-H '{name}: {value}'")
        raw = getattr(request, "raw_content", None) or b""
        if raw:
            body, _ = _decode_body(raw, request.headers)
            parts.append("--data-raw")
            parts.append(f"'{body}'")
        parts.append(f"'{request.pretty_url}'")
        return " ".join(parts)

    def request_url(self, flow_id: str) -> str:
        with self._lock:
            flow_obj = self._flows.get(flow_id)
        if flow_obj is None or getattr(flow_obj, "request", None) is None:
            return ""
        return getattr(flow_obj.request, "pretty_url", "") or ""

    def _emit_state(self) -> None:
        self._state.cert_exists = CERT_FILE.exists()
        try:
            self._on_state_changed(self._state)
        except Exception:
            pass

    def _record_flow(self, kind: str, flow_obj) -> None:
        if self._state.paused and kind != "response":
            return
        if kind not in {"request", "response", "error"}:
            return
        summary = summarize_flow(flow_obj)
        with self._lock:
            self._flows[summary.id] = flow_obj
            existing_index = -1
            for idx, row in enumerate(self._rows):
                if row.id == summary.id:
                    existing_index = idx
                    break
            if existing_index >= 0:
                self._rows[existing_index] = summary
            else:
                self._rows.insert(0, summary)
                if len(self._rows) > MAX_ROWS:
                    overflow = self._rows[MAX_ROWS:]
                    self._rows = self._rows[:MAX_ROWS]
                    for stale in overflow:
                        self._flows.pop(stale.id, None)
        try:
            self._on_flow_event(kind, summary)
        except Exception:
            pass


class _CollectorAddon:
    def __init__(self, service: PacketCaptureService) -> None:
        self._service = service

    def request(self, flow) -> None:  # pragma: no cover - integration
        self._service._record_flow("request", flow)

    def response(self, flow) -> None:  # pragma: no cover - integration
        self._service._record_flow("response", flow)

    def error(self, flow) -> None:  # pragma: no cover - integration
        self._service._record_flow("error", flow)


def filter_rows(
    rows: Iterable[FlowSummary],
    *,
    keyword: str = "",
    method: str = "",
    status_min: int = 0,
    status_max: int = 0,
    content_type: str = "",
    only_errors: bool = False,
) -> list[FlowSummary]:
    out: list[FlowSummary] = []
    keyword_lower = keyword.lower()
    method_lower = method.lower()
    content_type_lower = content_type.lower()
    for row in rows:
        if keyword_lower:
            haystack = f"{row.host}{row.path}{row.method}{row.content_type}".lower()
            if keyword_lower not in haystack:
                continue
        if method_lower and row.method.lower() != method_lower:
            continue
        if status_min and row.status < status_min:
            continue
        if status_max and row.status and row.status > status_max:
            continue
        if content_type_lower and content_type_lower not in row.content_type.lower():
            continue
        if only_errors and row.status < 400 and not row.error:
            continue
        out.append(row)
    return out

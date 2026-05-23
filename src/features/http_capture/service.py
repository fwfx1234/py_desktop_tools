from __future__ import annotations

import asyncio
import json
import os
import shlex
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import parse_qsl, urlsplit
from xml.dom import minidom

DEFAULT_LISTEN_HOST = "127.0.0.1"
LAN_LISTEN_HOST = "0.0.0.0"
DEFAULT_LISTEN_PORT = 8899
DEFAULT_PORT_TRY = 8
CERT_DIRECTORY = Path.home() / ".mitmproxy"
CERT_FILE = CERT_DIRECTORY / "mitmproxy-ca-cert.pem"
MITM_INSTALL_URL = "http://mitm.it"


@dataclass(slots=True)
class CaptureState:
    running: bool = False
    paused: bool = False
    listen_host: str = DEFAULT_LISTEN_HOST
    listen_port: int = 0
    cert_path: str = ""
    cert_exists: bool = False
    proxy_url: str = ""
    mobile_proxy_url: str = ""
    lan_ip: str = ""
    listen_mode: str = "local"
    https_decrypt_enabled: bool = True
    cert_install_url: str = MITM_INSTALL_URL
    system_proxy_enabled: bool = False
    system_proxy_supported: bool = False
    system_proxy_recoverable: bool = False
    system_proxy_recovery_message: str = ""
    system_proxy_error: str = ""
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
            "mobileProxyUrl": self.mobile_proxy_url,
            "lanIp": self.lan_ip,
            "listenMode": self.listen_mode,
            "httpsDecryptEnabled": self.https_decrypt_enabled,
            "certInstallUrl": self.cert_install_url,
            "systemProxyEnabled": self.system_proxy_enabled,
            "systemProxySupported": self.system_proxy_supported,
            "systemProxyRecoverable": self.system_proxy_recoverable,
            "systemProxyRecoveryMessage": self.system_proxy_recovery_message,
            "systemProxyError": self.system_proxy_error,
            "error": self.error,
        }


@dataclass(slots=True)
class FlowSummary:
    id: str
    method: str
    scheme: str
    host: str
    path: str
    url: str
    status: int
    content_type: str
    size: int
    request_size: int
    response_size: int
    duration_ms: int
    started_at: str
    started_iso: str
    encrypted: bool = False
    source: str = "capture"
    replayed: bool = False
    error: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "method": self.method,
            "scheme": self.scheme,
            "host": self.host,
            "path": self.path,
            "url": self.url,
            "status": self.status,
            "contentType": self.content_type,
            "size": self.size,
            "requestSize": self.request_size,
            "responseSize": self.response_size,
            "totalSize": self.request_size + self.response_size,
            "durationMs": self.duration_ms,
            "startedAt": self.started_at,
            "startedIso": self.started_iso,
            "encrypted": self.encrypted,
            "source": self.source,
            "replayed": self.replayed,
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
    request_size: int = 0
    response_status: int = 0
    response_reason: str = ""
    response_headers: list[tuple[str, str]] = field(default_factory=list)
    response_body: str = ""
    response_body_truncated: bool = False
    response_size: int = 0
    duration_ms: int = 0
    started_at: str = ""
    started_iso: str = ""
    query_params: list[tuple[str, str]] = field(default_factory=list)
    request_cookies: list[tuple[str, str]] = field(default_factory=list)
    response_cookies: list[tuple[str, str]] = field(default_factory=list)
    source: str = "capture"
    replayed: bool = False
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "requestUrl": self.request_url,
            "requestMethod": self.request_method,
            "requestHeaders": [{"name": k, "value": v} for k, v in self.request_headers],
            "requestBody": self.request_body,
            "requestBodyDisplay": _format_body_text(self.request_body, self.request_headers),
            "requestBodyTruncated": self.request_body_truncated,
            "requestBodyParams": [{"name": k, "value": v} for k, v in _body_params(self.request_body, self.request_headers)],
            "requestSize": self.request_size,
            "responseStatus": self.response_status,
            "responseReason": self.response_reason,
            "responseHeaders": [{"name": k, "value": v} for k, v in self.response_headers],
            "responseBody": self.response_body,
            "responseBodyDisplay": _format_body_text(self.response_body, self.response_headers),
            "responseBodyTruncated": self.response_body_truncated,
            "responseBodyParams": [{"name": k, "value": v} for k, v in _body_params(self.response_body, self.response_headers)],
            "responseSize": self.response_size,
            "durationMs": self.duration_ms,
            "startedAt": self.started_at,
            "startedIso": self.started_iso,
            "queryParams": [{"name": k, "value": v} for k, v in self.query_params],
            "requestCookies": [{"name": k, "value": v} for k, v in self.request_cookies],
            "responseCookies": [{"name": k, "value": v} for k, v in self.response_cookies],
            "source": self.source,
            "replayed": self.replayed,
            "note": self.note,
        }


MAX_BODY_BYTES = 64 * 1024
MAX_ROWS = 500
STATIC_EXTENSIONS = (
    ".css",
    ".js",
    ".map",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
)
STATIC_CONTENT_PREFIXES = (
    "image/",
    "font/",
    "text/css",
    "application/javascript",
    "text/javascript",
)
_AUTO_SYSTEM_PROXY = object()


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
    request_size = 0
    if request is not None:
        request_size = len(_message_content(request))
    response_size = 0
    if response is not None:
        response_size = len(_message_content(response))
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
    started_iso = _timestamp_iso(timestamp_start)
    encrypted = bool(getattr(request, "url", "").startswith("https://")) if request else False
    flow_id = getattr(flow_obj, "id", "") or f"flow-{time.time_ns()}"
    return FlowSummary(
        id=flow_id,
        method=method,
        scheme=scheme,
        host=host,
        path=path,
        url=pretty_url,
        status=status,
        content_type=content_type,
        size=response_size,
        request_size=request_size,
        response_size=response_size,
        duration_ms=duration_ms,
        started_at=started_at,
        started_iso=started_iso,
        encrypted=encrypted,
        error=error,
    )


def flow_detail(flow_obj) -> FlowDetail:
    request = getattr(flow_obj, "request", None)
    response = getattr(flow_obj, "response", None)
    timestamp_start = getattr(request, "timestamp_start", None) if request else None
    timestamp_end = getattr(response, "timestamp_end", None) if response else None
    duration_ms = 0
    if timestamp_start is not None and timestamp_end is not None:
        duration_ms = int(max(0, (float(timestamp_end) - float(timestamp_start)) * 1000))
    request_url = getattr(request, "pretty_url", "") if request else ""
    detail = FlowDetail(
        id=getattr(flow_obj, "id", ""),
        request_url=request_url,
        request_method=getattr(request, "method", "") if request else "",
        duration_ms=duration_ms,
        started_at=time.strftime("%H:%M:%S", time.localtime(float(timestamp_start))) if timestamp_start is not None else "",
        started_iso=_timestamp_iso(timestamp_start),
        query_params=_query_params(request_url),
    )
    if request is not None:
        detail.request_headers = _headers_list(request.headers)
        raw = _message_content(request)
        detail.request_size = len(raw)
        body, truncated = _decode_body(raw, request.headers)
        detail.request_body = body
        detail.request_body_truncated = truncated
        detail.request_cookies = _request_cookies(detail.request_headers)
    if response is not None:
        detail.response_status = int(getattr(response, "status_code", 0) or 0)
        detail.response_reason = getattr(response, "reason", "") or ""
        detail.response_headers = _headers_list(response.headers)
        raw = _message_content(response)
        detail.response_size = len(raw)
        body, truncated = _decode_body(raw, response.headers)
        detail.response_body = body
        detail.response_body_truncated = truncated
        detail.response_cookies = _response_cookies(detail.response_headers)
    return detail


def _headers_list(headers) -> list[tuple[str, str]]:
    if headers is None:
        return []
    try:
        return [(str(name), str(value)) for name, value in headers.items()]
    except Exception:
        return []


def _message_content(message) -> bytes:
    if message is None:
        return b""
    get_content = getattr(message, "get_content", None)
    if callable(get_content):
        for kwargs in ({"strict": False}, {}):
            try:
                data = get_content(**kwargs)
            except Exception:
                continue
            if data is not None:
                return _bytes_value(data)
    raw = getattr(message, "raw_content", None)
    if raw is not None:
        return _bytes_value(raw)
    content = getattr(message, "content", None)
    if content is not None:
        return _bytes_value(content)
    return b""


def _bytes_value(value) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, str):
        return value.encode("utf-8")
    try:
        return bytes(value)
    except Exception:
        return str(value).encode("utf-8", errors="replace")


def _timestamp_iso(value) -> str:
    if value is None:
        return ""
    try:
        return datetime.fromtimestamp(float(value)).astimezone().isoformat()
    except Exception:
        return ""


def _query_params(url: str) -> list[tuple[str, str]]:
    if not url:
        return []
    try:
        return [(str(name), str(value)) for name, value in parse_qsl(urlsplit(url).query, keep_blank_values=True)]
    except Exception:
        return []


def _header_value(headers: Iterable[tuple[str, str]], name: str) -> str:
    target = name.lower()
    for key, value in headers:
        if key.lower() == target:
            return value
    return ""


def _request_cookies(headers: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    value = _header_value(headers, "cookie")
    if not value:
        return []
    cookies: list[tuple[str, str]] = []
    for segment in value.split(";"):
        part = segment.strip()
        if not part:
            continue
        if "=" in part:
            name, cookie_value = part.split("=", 1)
        else:
            name, cookie_value = part, ""
        cookies.append((name.strip(), cookie_value.strip()))
    return cookies


def _response_cookies(headers: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    cookies: list[tuple[str, str]] = []
    for key, value in headers:
        if key.lower() != "set-cookie":
            continue
        first = value.split(";", 1)[0].strip()
        if not first:
            continue
        if "=" in first:
            name, cookie_value = first.split("=", 1)
        else:
            name, cookie_value = first, ""
        cookies.append((name.strip(), cookie_value.strip()))
    return cookies


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
        if hasattr(headers, "get"):
            ctype = headers.get("content-type") or headers.get("Content-Type")
        else:
            ctype = _header_value(headers, "content-type")
        if ctype:
            parts = [p.strip() for p in ctype.split(";")]
            for part in parts:
                if part.lower().startswith("charset="):
                    encoding = part.split("=", 1)[1].strip().strip("\"' ") or "utf-8"
    try:
        return payload.decode(encoding, errors="replace"), truncated
    except Exception:
        return payload.decode("utf-8", errors="replace"), truncated


def _format_body_text(text: str, headers: Iterable[tuple[str, str]]) -> str:
    if not text:
        return ""
    content_type = _header_value(headers, "content-type").lower()
    stripped = text.strip()
    if not stripped:
        return text
    if _looks_like_json(content_type, stripped):
        formatted = _format_json_text(stripped)
        if formatted:
            return formatted
    if _looks_like_form(content_type):
        formatted = _format_form_text(stripped)
        if formatted:
            return formatted
    if _looks_like_xml(content_type, stripped):
        formatted = _format_xml_text(stripped)
        if formatted:
            return formatted
    return text


def _body_params(text: str, headers: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    if not text:
        return []
    content_type = _header_value(headers, "content-type").lower()
    stripped = text.strip()
    if _looks_like_form(content_type):
        return [(str(name), str(value)) for name, value in parse_qsl(stripped, keep_blank_values=True)]
    if _looks_like_json(content_type, stripped):
        try:
            data = json.loads(stripped)
        except Exception:
            return []
        return _flatten_json_params(data)
    return []


def _looks_like_json(content_type: str, text: str) -> bool:
    return "json" in content_type or text.startswith("{") or text.startswith("[")


def _looks_like_form(content_type: str) -> bool:
    return "application/x-www-form-urlencoded" in content_type


def _looks_like_xml(content_type: str, text: str) -> bool:
    return "xml" in content_type or text.startswith("<?xml") or (text.startswith("<") and text.endswith(">"))


def _format_json_text(text: str) -> str:
    try:
        return json.dumps(json.loads(text), ensure_ascii=False, indent=2)
    except Exception:
        return ""


def _format_form_text(text: str) -> str:
    try:
        items = parse_qsl(text, keep_blank_values=True)
    except Exception:
        return ""
    if not items:
        return ""
    width = max(len(name) for name, _ in items)
    return "\n".join(f"{name.ljust(width)} = {value}" for name, value in items)


def _format_xml_text(text: str) -> str:
    try:
        parsed = minidom.parseString(text.encode("utf-8"))
        pretty = parsed.toprettyxml(indent="  ")
    except Exception:
        return ""
    return "\n".join(line for line in pretty.splitlines() if line.strip())


def _flatten_json_params(value: object, prefix: str = "") -> list[tuple[str, str]]:
    if isinstance(value, Mapping):
        items: list[tuple[str, str]] = []
        for key, item in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            items.extend(_flatten_json_params(item, name))
        return items
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items = []
        for index, item in enumerate(value):
            name = f"{prefix}[{index}]" if prefix else f"[{index}]"
            items.extend(_flatten_json_params(item, name))
        return items
    return [(prefix or "$", "" if value is None else str(value))]


def _headers_dict(headers: Iterable[tuple[str, str]]) -> dict[str, str]:
    output: dict[str, str] = {}
    for name, value in headers:
        lower = name.lower()
        if lower in {"host", "content-length", "transfer-encoding", "connection", "proxy-connection"}:
            continue
        output[name] = value
    return output


def _curl_arg(value: object) -> str:
    return shlex.quote(str(value))


def parse_header_lines(text: str) -> list[tuple[str, str]]:
    headers: list[tuple[str, str]] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        name = name.strip()
        if not name:
            continue
        headers.append((name, value.strip()))
    return headers


def _is_static_row(row: FlowSummary) -> bool:
    path = (row.path or "").lower()
    content_type = (row.content_type or "").lower()
    if any(path.endswith(ext) for ext in STATIC_EXTENSIONS):
        return True
    return any(content_type.startswith(prefix) for prefix in STATIC_CONTENT_PREFIXES)


class HttpCaptureService:
    def __init__(
        self,
        on_state_changed: Callable[[CaptureState], None],
        on_flow_event: Callable[[str, FlowSummary], None],
        data_dir: Path | None = None,
        system_proxy_controller: object = _AUTO_SYSTEM_PROXY,
    ) -> None:
        self._on_state_changed = on_state_changed
        self._on_flow_event = on_flow_event
        self._state = CaptureState(cert_path=str(CERT_FILE), cert_exists=CERT_FILE.exists())
        self._state.lan_ip = local_lan_ip()
        self._flows: dict[str, object] = {}
        self._detail_overrides: dict[str, FlowDetail] = {}
        self._rows: list[FlowSummary] = []
        self._lock = threading.Lock()
        self._master = None
        self._loop = None
        self._thread: threading.Thread | None = None
        self._started_event = threading.Event()
        self._start_error: str | None = None
        self._system_proxy = create_system_proxy_controller() if system_proxy_controller is _AUTO_SYSTEM_PROXY else system_proxy_controller
        self._system_proxy_snapshot = None
        self._state.system_proxy_supported = self._system_proxy is not None
        self._lease_store = ProxyLeaseStore(data_dir)
        self.recover_system_proxy_if_needed()

    @property
    def state(self) -> CaptureState:
        return self._state

    def cert_directory(self) -> Path:
        return CERT_DIRECTORY

    def cert_path(self) -> Path:
        return CERT_FILE

    def cert_install_url(self) -> str:
        return MITM_INSTALL_URL

    def local_lan_ip(self) -> str:
        return local_lan_ip()

    def install_desktop_certificate(self) -> tuple[bool, str]:
        if not CERT_FILE.exists():
            return False, "证书未生成，请先启动一次代理"
        if sys.platform == "win32":
            return _install_windows_certificate(CERT_FILE)
        if sys.platform == "darwin":
            return _install_macos_certificate(CERT_FILE)
        return False, f"当前平台暂不支持自动信任证书，请手动安装 {CERT_FILE}"

    def recover_system_proxy_if_needed(self) -> CaptureState:
        controller = self._system_proxy
        self._state.system_proxy_supported = controller is not None
        self._state.system_proxy_recoverable = self._lease_store.exists()
        self._state.system_proxy_recovery_message = ""
        if controller is None:
            if self._lease_store.exists():
                self._state.system_proxy_error = "发现上次代理接管记录，但当前平台不支持自动恢复"
            return self._state
        lease = self._lease_store.load()
        if not lease:
            return self._state
        try:
            if controller.is_current_proxy(lease.get("host", ""), int(lease.get("port") or 0)):
                controller.restore(lease.get("snapshot"))
                self._state.system_proxy_recovery_message = "已恢复上次异常退出残留的系统代理"
                self._state.system_proxy_error = ""
            else:
                self._state.system_proxy_recovery_message = "检测到系统代理已被修改，已清理旧接管记录"
        except Exception as exc:
            self._state.system_proxy_error = f"系统代理恢复失败: {exc}"
            self._state.system_proxy_recoverable = True
            return self._state
        self._lease_store.clear()
        self._state.system_proxy_recoverable = False
        self._state.system_proxy_enabled = False
        return self._state

    def start(
        self,
        host: str = DEFAULT_LISTEN_HOST,
        start_port: int = DEFAULT_LISTEN_PORT,
        *,
        mobile: bool = False,
    ) -> CaptureState:
        if self._state.running:
            return self._state
        self.recover_system_proxy_if_needed()
        try:
            port = find_free_port(host, start_port)
        except Exception as exc:
            self._state.error = f"无可用端口: {exc}"
            self._emit_state()
            return self._state

        from mitmproxy import options
        from mitmproxy.tools.dump import DumpMaster
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
                master = DumpMaster(opts, loop=loop, with_termlog=False, with_dumper=False)
                addon = _CollectorAddon(self)
                try:
                    master.addons.remove(master.addons.get("errorcheck"))
                except Exception:
                    pass
                master.addons.add(addon)
                self._master = master
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
                if self._state.running:
                    self._restore_system_proxy()
                    self._state.running = False
                    self._state.paused = False
                    self._state.proxy_url = ""
                    self._emit_state()

        self._thread = threading.Thread(target=runner, name="http-capture-proxy", daemon=True)
        self._thread.start()
        if not self._started_event.wait(timeout=5.0):
            master = self._master
            loop = self._loop
            if master is not None and loop is not None:
                try:
                    loop.call_soon_threadsafe(master.shutdown)
                except Exception:
                    pass
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
        self._state.listen_mode = "mobile" if mobile or host == LAN_LISTEN_HOST else "local"
        self._state.lan_ip = local_lan_ip()
        self._state.mobile_proxy_url = f"http://{self._state.lan_ip}:{port}" if self._state.lan_ip else ""
        if host == LAN_LISTEN_HOST:
            self._state.proxy_url = f"http://127.0.0.1:{port}"
        self._state.cert_exists = CERT_FILE.exists()
        self._state.error = ""
        self._enable_system_proxy(DEFAULT_LISTEN_HOST if host == LAN_LISTEN_HOST else host, port)
        self._emit_state()
        return self._state

    def start_mobile(self, start_port: int = DEFAULT_LISTEN_PORT) -> CaptureState:
        return self.start(LAN_LISTEN_HOST, start_port, mobile=True)

    def stop(self) -> CaptureState:
        self._restore_system_proxy()
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
        self._state.proxy_url = ""
        self._state.mobile_proxy_url = ""
        self._state.listen_mode = "local"
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
            self._detail_overrides.clear()
        return []

    def rows(self) -> list[FlowSummary]:
        with self._lock:
            return list(self._rows)

    def detail(self, flow_id: str) -> FlowDetail | None:
        with self._lock:
            override = self._detail_overrides.get(flow_id)
            flow_obj = self._flows.get(flow_id)
        if override is not None:
            return override
        if flow_obj is None:
            return None
        return flow_detail(flow_obj)

    def stats(self, visible_rows: Iterable[FlowSummary] | None = None) -> dict:
        with self._lock:
            all_rows = list(self._rows)
        rows = list(visible_rows) if visible_rows is not None else all_rows
        total_bytes = sum(row.request_size + row.response_size for row in rows)
        completed_durations = [row.duration_ms for row in rows if row.duration_ms > 0]
        hosts: dict[str, int] = {}
        methods: dict[str, int] = {}
        status_2xx = status_3xx = status_4xx = status_5xx = 0
        pending = errors = replayed = https = 0
        for row in rows:
            if row.host:
                hosts[row.host] = hosts.get(row.host, 0) + 1
            if row.method:
                methods[row.method] = methods.get(row.method, 0) + 1
            if row.status == 0 and not row.error:
                pending += 1
            elif row.status >= 500:
                status_5xx += 1
            elif row.status >= 400:
                status_4xx += 1
            elif row.status >= 300:
                status_3xx += 1
            elif row.status >= 200:
                status_2xx += 1
            if row.error or row.status >= 400:
                errors += 1
            if row.replayed:
                replayed += 1
            if row.encrypted:
                https += 1
        top_host = ""
        if hosts:
            top_host = sorted(hosts.items(), key=lambda item: (-item[1], item[0]))[0][0]
        method_counts = [
            {"name": name, "count": count}
            for name, count in sorted(methods.items(), key=lambda item: (-item[1], item[0]))
        ]
        return {
            "totalRows": len(all_rows),
            "visibleRows": len(rows),
            "errorRows": errors,
            "pendingRows": pending,
            "replayedRows": replayed,
            "httpsRows": https,
            "totalBytes": total_bytes,
            "avgDurationMs": int(sum(completed_durations) / len(completed_durations)) if completed_durations else 0,
            "topHost": top_host,
            "status2xx": status_2xx,
            "status3xx": status_3xx,
            "status4xx": status_4xx,
            "status5xx": status_5xx,
            "methods": method_counts,
        }

    def save_response_body(self, flow_id: str, target: Path) -> tuple[bool, str]:
        with self._lock:
            flow_obj = self._flows.get(flow_id)
            override = self._detail_overrides.get(flow_id)
        if override is not None and override.response_body:
            raw = override.response_body.encode("utf-8")
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            except Exception as exc:
                return False, f"保存失败: {exc}"
            return True, str(target)
        if flow_obj is None or getattr(flow_obj, "response", None) is None:
            return False, "未找到响应正文"
        raw = _message_content(flow_obj.response)
        if not raw:
            return False, "响应正文为空"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        except Exception as exc:
            return False, f"保存失败: {exc}"
        return True, str(target)

    def export_rows(self, flow_ids: Iterable[str], target: Path, export_format: str) -> tuple[bool, str]:
        ids = [flow_id for flow_id in flow_ids if flow_id]
        if not ids:
            return False, "没有可导出的会话"
        with self._lock:
            summaries = {row.id: row for row in self._rows if row.id in ids}
        details = []
        for flow_id in ids:
            summary = summaries.get(flow_id)
            detail = self.detail(flow_id)
            if summary is None or detail is None:
                continue
            details.append((summary, detail))
        if not details:
            return False, "没有可导出的会话"
        fmt = (export_format or "").lower()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if fmt == "har":
                payload = _build_har(details)
            else:
                payload = {
                    "version": 1,
                    "exportedAt": datetime.now().astimezone().isoformat(),
                    "sessions": [
                        {"summary": summary.to_dict(), "detail": detail.to_dict()}
                        for summary, detail in details
                    ],
                }
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            return False, f"导出失败: {exc}"
        return True, str(target)

    def build_curl(self, flow_id: str) -> str:
        with self._lock:
            flow_obj = self._flows.get(flow_id)
            override = self._detail_overrides.get(flow_id)
        if override is not None and override.request_url:
            parts = ["curl", "-X", _curl_arg(override.request_method or "GET")]
            for name, value in override.request_headers:
                parts.extend(["-H", _curl_arg(f"{name}: {value}")])
            if override.request_body:
                parts.extend(["--data-raw", _curl_arg(override.request_body)])
            parts.append(_curl_arg(override.request_url))
            return " ".join(parts)
        if flow_obj is None or getattr(flow_obj, "request", None) is None:
            return ""
        request = flow_obj.request
        parts = ["curl", "-X", _curl_arg(request.method)]
        for name, value in _headers_list(request.headers):
            parts.extend(["-H", _curl_arg(f"{name}: {value}")])
        raw = _message_content(request)
        if raw:
            body, _ = _decode_body(raw, request.headers)
            parts.extend(["--data-raw", _curl_arg(body)])
        parts.append(_curl_arg(request.pretty_url))
        return " ".join(parts)

    def request_url(self, flow_id: str) -> str:
        with self._lock:
            flow_obj = self._flows.get(flow_id)
            override = self._detail_overrides.get(flow_id)
        if override is not None:
            return override.request_url
        if flow_obj is None or getattr(flow_obj, "request", None) is None:
            return ""
        return getattr(flow_obj.request, "pretty_url", "") or ""

    def replay_flow(self, flow_id: str) -> tuple[bool, str, FlowSummary | None]:
        with self._lock:
            flow_obj = self._flows.get(flow_id)
            override = self._detail_overrides.get(flow_id)
        if flow_obj is not None and getattr(flow_obj, "request", None) is not None:
            request = flow_obj.request
            method = getattr(request, "method", "GET") or "GET"
            url = getattr(request, "pretty_url", "") or ""
            headers = _headers_dict(_headers_list(request.headers))
            body = _message_content(request)
        elif override is not None and override.request_url:
            method = override.request_method or "GET"
            url = override.request_url
            headers = _headers_dict(override.request_headers)
            body = override.request_body.encode("utf-8") if override.request_body else b""
        else:
            return False, "未找到可重放的请求", None
        if not url:
            return False, "请求 URL 为空", None
        try:
            import requests
        except Exception as exc:
            return False, f"requests 不可用: {exc}", None
        started = time.time()
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=body if body else None,
                timeout=30,
                verify=False,
                allow_redirects=False,
            )
        except Exception as exc:
            summary, detail = _replay_error_summary(flow_id, method, url, headers, body, started, exc)
            self._store_replay(summary, detail)
            return False, f"重放失败: {exc}", summary
        elapsed_ms = int(max(0, (time.time() - started) * 1000))
        summary, detail = _replay_response_summary(flow_id, method, url, headers, body, started, elapsed_ms, response)
        self._store_replay(summary, detail)
        return True, f"重放完成: HTTP {response.status_code} · {elapsed_ms}ms", summary

    def send_composer_request(
        self,
        method: str,
        url: str,
        headers_text: str = "",
        body_text: str = "",
    ) -> tuple[bool, str, FlowSummary | None]:
        clean_method = (method or "GET").strip().upper() or "GET"
        clean_url = (url or "").strip()
        if not clean_url:
            return False, "请输入请求 URL", None
        if not clean_url.startswith(("http://", "https://")):
            return False, "URL 必须以 http:// 或 https:// 开头", None
        headers = _headers_dict(parse_header_lines(headers_text))
        body = body_text.encode("utf-8") if body_text else b""
        try:
            import requests
        except Exception as exc:
            return False, f"requests 不可用: {exc}", None
        started = time.time()
        try:
            response = requests.request(
                method=clean_method,
                url=clean_url,
                headers=headers,
                data=body if body else None,
                timeout=30,
                verify=False,
                allow_redirects=False,
            )
        except Exception as exc:
            summary, detail = _sent_error_summary(clean_method, clean_url, headers, body, started, exc)
            self._store_manual(summary, detail)
            return False, f"发送失败: {exc}", summary
        elapsed_ms = int(max(0, (time.time() - started) * 1000))
        summary, detail = _sent_response_summary(clean_method, clean_url, headers, body, started, elapsed_ms, response)
        self._store_manual(summary, detail)
        return True, f"发送完成: HTTP {response.status_code} · {elapsed_ms}ms", summary

    def _emit_state(self) -> None:
        self._state.cert_exists = CERT_FILE.exists()
        try:
            self._on_state_changed(self._state)
        except Exception:
            pass

    def _enable_system_proxy(self, host: str, port: int) -> None:
        controller = self._system_proxy
        self._state.system_proxy_supported = controller is not None
        self._state.system_proxy_error = ""
        if controller is None:
            return
        try:
            self._system_proxy_snapshot = controller.snapshot()
            self._lease_store.save(host, port, self._system_proxy_snapshot)
            controller.enable(host, port)
        except Exception as exc:
            self._state.system_proxy_enabled = False
            self._state.system_proxy_recoverable = self._lease_store.exists()
            self._state.system_proxy_error = f"系统代理设置失败: {exc}"
            return
        self._state.system_proxy_enabled = True
        self._state.system_proxy_recoverable = True

    def _restore_system_proxy(self) -> None:
        controller = self._system_proxy
        snapshot = self._system_proxy_snapshot
        lease = self._lease_store.load()
        if snapshot is None:
            snapshot = lease.get("snapshot") if lease else None
        self._state.system_proxy_supported = controller is not None
        if controller is None or snapshot is None:
            self._state.system_proxy_enabled = False
            return
        try:
            if lease and not controller.is_current_proxy(lease.get("host", ""), int(lease.get("port") or 0)):
                self._state.system_proxy_recovery_message = "检测到系统代理已被修改，已清理旧接管记录"
                self._lease_store.clear()
                return
            controller.restore(snapshot)
            self._state.system_proxy_error = ""
            self._lease_store.clear()
        except Exception as exc:
            self._state.system_proxy_error = f"系统代理恢复失败: {exc}"
        finally:
            self._system_proxy_snapshot = None
            self._state.system_proxy_enabled = False
            self._state.system_proxy_recoverable = self._lease_store.exists()

    def _mark_proxy_running(self) -> None:
        self._started_event.set()

    def _record_flow(self, kind: str, flow_obj) -> None:
        if kind not in {"request", "response", "error"}:
            return
        if self._state.paused:
            if kind != "response":
                return
            flow_id = getattr(flow_obj, "id", "")
            with self._lock:
                known_flow = bool(flow_id and flow_id in self._flows)
            if not known_flow:
                return
        summary = summarize_flow(flow_obj)
        with self._lock:
            self._flows[summary.id] = flow_obj
            self._detail_overrides.pop(summary.id, None)
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
                        self._detail_overrides.pop(stale.id, None)
        try:
            self._on_flow_event(kind, summary)
        except Exception:
            pass

    def _store_replay(self, summary: FlowSummary, detail: FlowDetail) -> None:
        self._store_manual(summary, detail)

    def _store_manual(self, summary: FlowSummary, detail: FlowDetail) -> None:
        with self._lock:
            self._flows.pop(summary.id, None)
            self._detail_overrides[summary.id] = detail
            self._rows.insert(0, summary)
            if len(self._rows) > MAX_ROWS:
                overflow = self._rows[MAX_ROWS:]
                self._rows = self._rows[:MAX_ROWS]
                for stale in overflow:
                    self._flows.pop(stale.id, None)
                    self._detail_overrides.pop(stale.id, None)
        try:
            self._on_flow_event(summary.source, summary)
        except Exception:
            pass


class _CollectorAddon:
    def __init__(self, service: HttpCaptureService) -> None:
        self._service = service

    def running(self) -> None:  # pragma: no cover - integration
        self._service._mark_proxy_running()

    def request(self, flow) -> None:  # pragma: no cover - integration
        self._service._record_flow("request", flow)

    def response(self, flow) -> None:  # pragma: no cover - integration
        self._service._record_flow("response", flow)

    def error(self, flow) -> None:  # pragma: no cover - integration
        self._service._record_flow("error", flow)


class ProxyLeaseStore:
    def __init__(self, data_dir: Path | None = None) -> None:
        root = data_dir or _default_plugin_data_dir()
        self.path = root / "system_proxy_lease.json"

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> dict:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return raw if isinstance(raw, dict) else {}

    def save(self, host: str, port: int, snapshot) -> None:
        payload = {
            "version": 1,
            "pid": os.getpid(),
            "createdAt": datetime.now().astimezone().isoformat(),
            "host": host,
            "port": int(port),
            "snapshot": snapshot,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(self.path)

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        except Exception:
            pass


class WindowsSystemProxyController:
    def snapshot(self) -> dict:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WINDOWS_PROXY_KEY) as key:
            return {
                "ProxyEnable": _reg_query(key, "ProxyEnable", 0),
                "ProxyServer": _reg_query(key, "ProxyServer", ""),
                "ProxyOverride": _reg_query(key, "ProxyOverride", ""),
            }

    def enable(self, host: str, port: int) -> None:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WINDOWS_PROXY_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, f"http={host}:{port};https={host}:{port}")
            winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, "<local>")
        _windows_refresh_proxy_settings()

    def restore(self, snapshot: dict) -> None:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WINDOWS_PROXY_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, int(snapshot.get("ProxyEnable") or 0))
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, str(snapshot.get("ProxyServer") or ""))
            winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, str(snapshot.get("ProxyOverride") or ""))
        _windows_refresh_proxy_settings()

    def is_current_proxy(self, host: str, port: int) -> bool:
        snapshot = self.snapshot()
        if int(snapshot.get("ProxyEnable") or 0) != 1:
            return False
        return _proxy_server_matches(str(snapshot.get("ProxyServer") or ""), host, port)


class MacOSSystemProxyController:
    def snapshot(self) -> list[dict[str, str]]:
        services = _macos_network_services()
        snapshot = []
        for service in services:
            snapshot.append(
                {
                    "service": service,
                    "web": _run_networksetup(["-getwebproxy", service]),
                    "secure": _run_networksetup(["-getsecurewebproxy", service]),
                }
            )
        return snapshot

    def enable(self, host: str, port: int) -> None:
        for service in _macos_network_services():
            _run_networksetup(["-setwebproxy", service, host, str(port)])
            _run_networksetup(["-setsecurewebproxy", service, host, str(port)])
            _run_networksetup(["-setwebproxystate", service, "on"])
            _run_networksetup(["-setsecurewebproxystate", service, "on"])

    def restore(self, snapshot: list[dict[str, str]]) -> None:
        for item in snapshot:
            service = item["service"]
            web = _parse_networksetup_proxy(item.get("web", ""))
            secure = _parse_networksetup_proxy(item.get("secure", ""))
            _restore_macos_proxy(service, web, secure=False)
            _restore_macos_proxy(service, secure, secure=True)

    def is_current_proxy(self, host: str, port: int) -> bool:
        for service in _macos_network_services():
            web = _parse_networksetup_proxy(_run_networksetup(["-getwebproxy", service]))
            secure = _parse_networksetup_proxy(_run_networksetup(["-getsecurewebproxy", service]))
            if _macos_proxy_matches(web, host, port) or _macos_proxy_matches(secure, host, port):
                return True
        return False


_WINDOWS_PROXY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"


def _default_plugin_data_dir() -> Path:
    configured = os.getenv("PY_DESKTOP_TOOLS_DATA_DIR", "").strip()
    if configured:
        root = Path(configured).expanduser()
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support" / "PyDesktopTools"
    elif sys.platform == "win32":
        root = Path(os.getenv("APPDATA", str(Path.home()))) / "PyDesktopTools"
    else:
        root = Path.home() / ".local" / "share" / "py-desktop-tools"
    return root / "plugins" / "http-capture"


def create_system_proxy_controller():
    if sys.platform == "win32":
        return WindowsSystemProxyController()
    if sys.platform == "darwin":
        return MacOSSystemProxyController()
    return None


def _reg_query(key, name: str, default):
    try:
        return __import__("winreg").QueryValueEx(key, name)[0]
    except FileNotFoundError:
        return default


def _windows_refresh_proxy_settings() -> None:
    try:
        import ctypes

        internet_set_option = ctypes.windll.Wininet.InternetSetOptionW
        internet_set_option(0, 39, 0, 0)
        internet_set_option(0, 37, 0, 0)
    except Exception:
        pass


def _install_windows_certificate(path: Path) -> tuple[bool, str]:
    completed = subprocess.run(
        ["certutil", "-user", "-addstore", "Root", str(path)],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if completed.returncode == 0:
        return True, "已信任 HTTPS 解密证书"
    message = (completed.stderr or completed.stdout or "").strip()
    return False, message or "证书安装失败"


def _install_macos_certificate(path: Path) -> tuple[bool, str]:
    completed = subprocess.run(
        [
            "security",
            "add-trusted-cert",
            "-d",
            "-r",
            "trustRoot",
            "-k",
            str(Path.home() / "Library" / "Keychains" / "login.keychain-db"),
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode == 0:
        return True, "已信任 HTTPS 解密证书"
    message = (completed.stderr or completed.stdout or "").strip()
    return False, message or "证书安装失败"


def _proxy_server_matches(value: str, host: str, port: int) -> bool:
    expected = {f"{host}:{port}", f"http://{host}:{port}"}
    for part in value.split(";"):
        item = part.strip()
        if not item:
            continue
        if "=" in item:
            _, item = item.split("=", 1)
            item = item.strip()
        if item in expected:
            return True
    return False


def local_lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
    except Exception:
        ip = ""
    if ip and not ip.startswith("127."):
        return ip
    try:
        host_name = socket.gethostname()
        for candidate in socket.gethostbyname_ex(host_name)[2]:
            if candidate and not candidate.startswith("127."):
                return candidate
    except Exception:
        pass
    return ""


def _macos_network_services() -> list[str]:
    output = _run_networksetup(["-listallnetworkservices"])
    services = []
    for line in output.splitlines():
        item = line.strip()
        if not item or item.startswith("An asterisk"):
            continue
        services.append(item.lstrip("*").strip())
    return services


def _run_networksetup(args: list[str]) -> str:
    completed = subprocess.run(
        ["networksetup", *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=8,
    )
    return completed.stdout


def _parse_networksetup_proxy(output: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in output.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip().lower()] = value.strip()
    return data


def _restore_macos_proxy(service: str, data: dict[str, str], *, secure: bool) -> None:
    prefix = "-setsecurewebproxy" if secure else "-setwebproxy"
    state_cmd = "-setsecurewebproxystate" if secure else "-setwebproxystate"
    enabled = (data.get("enabled") or "No").lower() in {"yes", "on", "1", "true"}
    server = data.get("server") or "127.0.0.1"
    port = data.get("port") or "8080"
    _run_networksetup([prefix, service, server, port])
    _run_networksetup([state_cmd, service, "on" if enabled else "off"])


def _macos_proxy_matches(data: dict[str, str], host: str, port: int) -> bool:
    enabled = (data.get("enabled") or "No").lower() in {"yes", "on", "1", "true"}
    if not enabled:
        return False
    return (data.get("server") or "") == host and str(data.get("port") or "") == str(port)


def filter_rows(
    rows: Iterable[FlowSummary],
    *,
    keyword: str = "",
    host: str = "",
    method: str = "",
    status_min: int = 0,
    status_max: int = 0,
    content_type: str = "",
    scheme: str = "",
    only_errors: bool = False,
    hide_static: bool = False,
    min_duration_ms: int = 0,
) -> list[FlowSummary]:
    out: list[FlowSummary] = []
    keyword_lower = keyword.lower()
    host_lower = host.lower()
    method_lower = method.lower()
    content_type_lower = content_type.lower()
    scheme_lower = scheme.lower()
    for row in rows:
        if keyword_lower:
            haystack = f"{row.host}{row.path}{row.url}{row.method}{row.content_type}{row.status}{row.note}".lower()
            if keyword_lower not in haystack:
                continue
        if host_lower and host_lower not in row.host.lower():
            continue
        if method_lower and row.method.lower() != method_lower:
            continue
        if scheme_lower and row.scheme.lower() != scheme_lower:
            continue
        if status_min and row.status < status_min:
            continue
        if status_max and row.status and row.status > status_max:
            continue
        if content_type_lower and content_type_lower not in row.content_type.lower():
            continue
        if only_errors and row.status < 400 and not row.error:
            continue
        if hide_static and _is_static_row(row):
            continue
        if min_duration_ms and row.duration_ms < min_duration_ms:
            continue
        out.append(row)
    return out


def _build_har(items: Iterable[tuple[FlowSummary, FlowDetail]]) -> dict:
    entries = []
    for summary, detail in items:
        request_headers = [{"name": name, "value": value} for name, value in detail.request_headers]
        response_headers = [{"name": name, "value": value} for name, value in detail.response_headers]
        mime_type = _header_value(detail.response_headers, "content-type") or summary.content_type
        request: dict = {
            "method": detail.request_method,
            "url": detail.request_url,
            "httpVersion": "HTTP/1.1",
            "headers": request_headers,
            "queryString": [{"name": name, "value": value} for name, value in detail.query_params],
            "cookies": [{"name": name, "value": value} for name, value in detail.request_cookies],
            "headersSize": -1,
            "bodySize": detail.request_size,
        }
        if detail.request_body:
            request["postData"] = {
                "mimeType": _header_value(detail.request_headers, "content-type"),
                "text": detail.request_body,
            }
        entries.append(
            {
                "startedDateTime": summary.started_iso or detail.started_iso or datetime.now().astimezone().isoformat(),
                "time": summary.duration_ms,
                "request": request,
                "response": {
                    "status": detail.response_status,
                    "statusText": detail.response_reason,
                    "httpVersion": "HTTP/1.1",
                    "headers": response_headers,
                    "cookies": [{"name": name, "value": value} for name, value in detail.response_cookies],
                    "content": {
                        "size": detail.response_size,
                        "mimeType": mime_type,
                        "text": detail.response_body if not detail.response_body_truncated else "",
                    },
                    "redirectURL": _header_value(detail.response_headers, "location"),
                    "headersSize": -1,
                    "bodySize": detail.response_size,
                },
                "cache": {},
                "timings": {"send": 0, "wait": summary.duration_ms, "receive": 0},
                "comment": summary.note or detail.note,
            }
        )
    return {
        "log": {
            "version": "1.2",
            "creator": {"name": "Suishou HTTP Capture", "version": "1.0"},
            "entries": entries,
        }
    }


def _replay_response_summary(
    source_flow_id: str,
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes,
    started: float,
    elapsed_ms: int,
    response,
) -> tuple[FlowSummary, FlowDetail]:
    parsed = urlsplit(url)
    response_headers = [(str(k), str(v)) for k, v in response.headers.items()]
    response_body = response.content or b""
    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
    flow_id = f"replay-{int(started * 1000)}"
    summary = FlowSummary(
        id=flow_id,
        method=method,
        scheme=parsed.scheme,
        host=parsed.hostname or "",
        path=parsed.path + (("?" + parsed.query) if parsed.query else ""),
        url=url,
        status=int(response.status_code or 0),
        content_type=content_type,
        size=len(response_body),
        request_size=len(body),
        response_size=len(response_body),
        duration_ms=elapsed_ms,
        started_at=time.strftime("%H:%M:%S", time.localtime(started)),
        started_iso=_timestamp_iso(started),
        encrypted=url.startswith("https://"),
        source="replay",
        replayed=True,
        note=f"重放自 {source_flow_id}",
    )
    request_body, request_truncated = _decode_body(body, headers)
    response_text, response_truncated = _decode_body(response_body, response.headers)
    detail = FlowDetail(
        id=flow_id,
        request_url=url,
        request_method=method,
        request_headers=list(headers.items()),
        request_body=request_body,
        request_body_truncated=request_truncated,
        request_size=len(body),
        response_status=int(response.status_code or 0),
        response_reason=getattr(response, "reason", "") or "",
        response_headers=response_headers,
        response_body=response_text,
        response_body_truncated=response_truncated,
        response_size=len(response_body),
        duration_ms=elapsed_ms,
        started_at=summary.started_at,
        started_iso=summary.started_iso,
        query_params=_query_params(url),
        request_cookies=_request_cookies(headers.items()),
        response_cookies=_response_cookies(response_headers),
        source="replay",
        replayed=True,
        note=summary.note,
    )
    return summary, detail


def _replay_error_summary(
    source_flow_id: str,
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes,
    started: float,
    exc: Exception,
) -> tuple[FlowSummary, FlowDetail]:
    parsed = urlsplit(url)
    elapsed_ms = int(max(0, (time.time() - started) * 1000))
    flow_id = f"replay-{int(started * 1000)}"
    message = str(exc)
    summary = FlowSummary(
        id=flow_id,
        method=method,
        scheme=parsed.scheme,
        host=parsed.hostname or "",
        path=parsed.path + (("?" + parsed.query) if parsed.query else ""),
        url=url,
        status=0,
        content_type="",
        size=0,
        request_size=len(body),
        response_size=0,
        duration_ms=elapsed_ms,
        started_at=time.strftime("%H:%M:%S", time.localtime(started)),
        started_iso=_timestamp_iso(started),
        encrypted=url.startswith("https://"),
        source="replay",
        replayed=True,
        error=message,
        note=f"重放自 {source_flow_id}",
    )
    request_body, request_truncated = _decode_body(body, headers)
    detail = FlowDetail(
        id=flow_id,
        request_url=url,
        request_method=method,
        request_headers=list(headers.items()),
        request_body=request_body,
        request_body_truncated=request_truncated,
        request_size=len(body),
        duration_ms=elapsed_ms,
        started_at=summary.started_at,
        started_iso=summary.started_iso,
        query_params=_query_params(url),
        request_cookies=_request_cookies(headers.items()),
        source="replay",
        replayed=True,
        note=message,
    )
    return summary, detail


def _sent_response_summary(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes,
    started: float,
    elapsed_ms: int,
    response,
) -> tuple[FlowSummary, FlowDetail]:
    parsed = urlsplit(url)
    response_headers = [(str(k), str(v)) for k, v in response.headers.items()]
    response_body = response.content or b""
    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
    flow_id = f"composer-{int(started * 1000)}"
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    summary = FlowSummary(
        id=flow_id,
        method=method,
        scheme=parsed.scheme,
        host=parsed.hostname or "",
        path=path,
        url=url,
        status=int(response.status_code or 0),
        content_type=content_type,
        size=len(response_body),
        request_size=len(body),
        response_size=len(response_body),
        duration_ms=elapsed_ms,
        started_at=time.strftime("%H:%M:%S", time.localtime(started)),
        started_iso=_timestamp_iso(started),
        encrypted=url.startswith("https://"),
        source="composer",
        note="Composer",
    )
    request_body, request_truncated = _decode_body(body, headers)
    response_text, response_truncated = _decode_body(response_body, response.headers)
    detail = FlowDetail(
        id=flow_id,
        request_url=url,
        request_method=method,
        request_headers=list(headers.items()),
        request_body=request_body,
        request_body_truncated=request_truncated,
        request_size=len(body),
        response_status=int(response.status_code or 0),
        response_reason=getattr(response, "reason", "") or "",
        response_headers=response_headers,
        response_body=response_text,
        response_body_truncated=response_truncated,
        response_size=len(response_body),
        duration_ms=elapsed_ms,
        started_at=summary.started_at,
        started_iso=summary.started_iso,
        query_params=_query_params(url),
        request_cookies=_request_cookies(headers.items()),
        response_cookies=_response_cookies(response_headers),
        source="composer",
        note="Composer",
    )
    return summary, detail


def _sent_error_summary(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes,
    started: float,
    exc: Exception,
) -> tuple[FlowSummary, FlowDetail]:
    parsed = urlsplit(url)
    elapsed_ms = int(max(0, (time.time() - started) * 1000))
    flow_id = f"composer-{int(started * 1000)}"
    message = str(exc)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    summary = FlowSummary(
        id=flow_id,
        method=method,
        scheme=parsed.scheme,
        host=parsed.hostname or "",
        path=path,
        url=url,
        status=0,
        content_type="",
        size=0,
        request_size=len(body),
        response_size=0,
        duration_ms=elapsed_ms,
        started_at=time.strftime("%H:%M:%S", time.localtime(started)),
        started_iso=_timestamp_iso(started),
        encrypted=url.startswith("https://"),
        source="composer",
        error=message,
        note="Composer",
    )
    request_body, request_truncated = _decode_body(body, headers)
    detail = FlowDetail(
        id=flow_id,
        request_url=url,
        request_method=method,
        request_headers=list(headers.items()),
        request_body=request_body,
        request_body_truncated=request_truncated,
        request_size=len(body),
        duration_ms=elapsed_ms,
        started_at=summary.started_at,
        started_iso=summary.started_iso,
        query_params=_query_params(url),
        request_cookies=_request_cookies(headers.items()),
        source="composer",
        note=message,
    )
    return summary, detail

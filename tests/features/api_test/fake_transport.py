from __future__ import annotations

"""Fake transport implementations for deterministic testing without network I/O."""

from collections.abc import Callable
import time

from features.api_test.transport import HttpDriver, HttpResponse, WsConnection, WsDriver


class FakeHttpDriver(HttpDriver):
    """Fake HTTP driver that returns canned responses or calls a factory."""

    def __init__(
        self,
        *,
        canned_response: HttpResponse | None = None,
        response_factory: Callable[..., HttpResponse] | None = None,
    ) -> None:
        self._canned = canned_response or HttpResponse(
            status_code=200,
            content=b'{"ok": true}',
            text='{"ok": true}',
            headers={"Content-Type": "application/json"},
            url="http://fake.example.com",
            elapsed_ms=10,
            json_data={"ok": True},
        )
        self._factory = response_factory
        self.calls: list[dict] = []

    def send(
        self,
        method: str,
        url: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        body: str | None = None,
        timeout: int = 20,
    ) -> HttpResponse:
        self.calls.append({
            "type": "send",
            "method": method,
            "url": url,
            "params": params,
            "headers": headers,
            "body": body,
            "timeout": timeout,
        })
        if self._factory:
            return self._factory(method=method, url=url, params=params, headers=headers, body=body, timeout=timeout)
        return self._canned

    def send_file(
        self,
        method: str,
        url: str,
        file_path: str,
        file_param: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int = 30,
    ) -> HttpResponse:
        self.calls.append({
            "type": "send_file",
            "method": method,
            "url": url,
            "file_path": file_path,
            "file_param": file_param,
            "params": params,
            "headers": headers,
            "timeout": timeout,
        })
        if self._factory:
            return self._factory(method=method, url=url, file_path=file_path, file_param=file_param, params=params, headers=headers, timeout=timeout)
        return self._canned


class FakeWsConnection(WsConnection):
    def __init__(self, url: str) -> None:
        self.url = url
        self.sent: list[str | bytes] = []
        self.closed = False
        self._receive_queue: list[str | bytes] = []

    def send(self, payload: str | bytes, opcode: int | None = None) -> None:
        self.sent.append(payload)

    def recv(self) -> str | bytes:
        if self._receive_queue:
            return self._receive_queue.pop(0)
        return "fake ws message"

    def close(self) -> None:
        self.closed = True


class FakeWsDriver(WsDriver):
    def __init__(self) -> None:
        self.connections: dict[str, FakeWsConnection] = {}
        self._next_connect_should_fail: bool = False
        self._fail_reason: str = "connection refused"

    def connect(
        self,
        url: str,
        header: list[str] | None = None,
        timeout: int = 10,
    ) -> WsConnection:
        if self._next_connect_should_fail:
            self._next_connect_should_fail = False
            raise OSError(self._fail_reason)
        conn = FakeWsConnection(url)
        self.connections[url] = conn
        return conn

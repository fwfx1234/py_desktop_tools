from __future__ import annotations

"""Real transport implementations backed by requests and websocket-client."""

import os
import time

from .transport import HttpDriver, HttpResponse, WsConnection, WsDriver


class RealHttpDriver(HttpDriver):
    """HTTP driver backed by the requests library."""

    def send(
        self,
        method: str,
        url: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        body: str | None = None,
        timeout: int = 20,
    ) -> HttpResponse:
        import requests

        started = time.perf_counter()
        resp = requests.request(
            method=method,
            url=url,
            params=params or {},
            headers=headers or {},
            data=body or None,
            timeout=timeout,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        json_data = None
        try:
            json_data = resp.json()
        except Exception:
            pass

        return HttpResponse(
            status_code=resp.status_code,
            reason=resp.reason or "",
            content=resp.content,
            text=resp.text,
            headers=dict(resp.headers),
            url=resp.url,
            elapsed_ms=elapsed_ms,
            request_method=resp.request.method if resp.request is not None else method,
            request_url=resp.request.url if resp.request is not None else url,
            request_headers=dict(resp.request.headers) if resp.request is not None else (headers or {}),
            request_body=resp.request.body if resp.request is not None else body,
            json_data=json_data,
        )

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
        import requests

        started = time.perf_counter()
        with open(file_path, "rb") as fh:
            resp = requests.request(
                method=method,
                url=url,
                params=params or {},
                headers=headers or {},
                files={file_param: (os.path.basename(file_path), fh)},
                timeout=timeout,
            )
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        json_data = None
        try:
            json_data = resp.json()
        except Exception:
            pass

        return HttpResponse(
            status_code=resp.status_code,
            reason=resp.reason or "",
            content=resp.content,
            text=resp.text,
            headers=dict(resp.headers),
            url=resp.url,
            elapsed_ms=elapsed_ms,
            request_method=resp.request.method if resp.request is not None else method,
            request_url=resp.request.url if resp.request is not None else url,
            request_headers=dict(resp.request.headers) if resp.request is not None else (headers or {}),
            request_body=None,
            json_data=json_data,
        )


class RealWsConnection(WsConnection):
    def __init__(self, ws) -> None:
        self._ws = ws

    def send(self, payload: str | bytes, opcode: int | None = None) -> None:
        if opcode is not None:
            self._ws.send(payload, opcode=opcode)
        else:
            self._ws.send(payload)

    def recv(self) -> str | bytes:
        return self._ws.recv()

    def close(self) -> None:
        self._ws.close()


class RealWsDriver(WsDriver):
    """WebSocket driver backed by the websocket-client library."""

    def connect(
        self,
        url: str,
        header: list[str] | None = None,
        timeout: int = 10,
    ) -> WsConnection:
        from websocket import create_connection

        ws = create_connection(url, header=header or None, timeout=timeout)
        return RealWsConnection(ws)

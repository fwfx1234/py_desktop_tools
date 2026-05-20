from __future__ import annotations

"""Transport abstractions for HTTP and WebSocket communication.

Protocols define the contract; real implementations wrap third-party libraries;
fake implementations enable deterministic testing without network access.
"""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class HttpResponse:
    """Normalized HTTP response, decoupled from the requests library."""

    status_code: int
    reason: str = ""
    content: bytes = b""
    text: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    url: str = ""
    elapsed_ms: int = 0
    request_method: str = ""
    request_url: str = ""
    request_headers: dict[str, str] = field(default_factory=dict)
    request_body: str | None = None
    json_data: object = None

    def json(self) -> object:
        if self.json_data is not None:
            return self.json_data
        import json

        return json.loads(self.text)


class HttpDriver(Protocol):
    """Abstracts HTTP request execution behind a pluggable transport."""

    def send(
        self,
        method: str,
        url: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        body: str | None = None,
        timeout: int = 20,
    ) -> HttpResponse:
        ...

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
        ...


class WsConnection(Protocol):
    """Abstracts a single WebSocket connection."""

    def send(self, payload: str | bytes, opcode: int | None = None) -> None: ...
    def recv(self) -> str | bytes: ...
    def close(self) -> None: ...


class WsDriver(Protocol):
    """Abstracts WebSocket connection factory behind a pluggable transport."""

    def connect(
        self,
        url: str,
        header: list[str] | None = None,
        timeout: int = 10,
    ) -> WsConnection:
        ...

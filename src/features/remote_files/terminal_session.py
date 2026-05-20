from __future__ import annotations

import re
import time
from threading import Event, Lock, Thread
from urllib.parse import unquote

from PySide6.QtCore import Property, QObject, Signal, Slot


_OSC7_RE = re.compile(r"\x1b\]7;file://[^/]*(/[^\x07\x1b]*)(?:\x07|\x1b\\)")


class RemoteTerminalBridge(QObject):
    output = Signal(str)
    closed = Signal(str)
    workingDirChanged = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("remoteTerminalBridge")
        self._channel = None
        self._closed = Event()
        self._reader: Thread | None = None
        self._cwd: str = ""
        self._cwd_lock = Lock()
        self._pwd_probe_deadline: float = 0.0

    @Slot(str)
    def sendInput(self, text: str) -> None:
        channel = self._channel
        if channel is None or self._closed.is_set():
            return
        try:
            channel.send(text)
        except Exception as exc:
            self.closed.emit(str(exc))

    @Slot(int, int)
    def resize(self, cols: int, rows: int) -> None:
        channel = self._channel
        if channel is None or self._closed.is_set():
            return
        try:
            channel.resize_pty(width=max(1, int(cols)), height=max(1, int(rows)))
        except Exception:
            return

    @Slot()
    def requestWorkingDir(self) -> None:
        """Send ``pwd`` to the terminal and arm a parser for the next output line."""

        channel = self._channel
        if channel is None or self._closed.is_set():
            return
        with self._cwd_lock:
            self._pwd_probe_deadline = time.monotonic() + 3.0
        try:
            channel.send("pwd\n")
        except Exception as exc:
            self.closed.emit(str(exc))

    def current_working_dir(self) -> str:
        with self._cwd_lock:
            return self._cwd

    @Property(str, notify=workingDirChanged)
    def workingDir(self) -> str:  # noqa: N802 - Qt naming
        return self.current_working_dir()

    def attach(self, channel) -> None:
        self.close()
        self._closed.clear()
        self._channel = channel
        self._reader = Thread(target=self._read_loop, name="remote-terminal-reader", daemon=True)
        self._reader.start()

    def close(self) -> None:
        self._closed.set()
        channel = self._channel
        self._channel = None
        if channel is not None:
            try:
                channel.close()
            except Exception:
                pass

    def _read_loop(self) -> None:
        channel = self._channel
        if channel is None:
            return
        try:
            while not self._closed.is_set():
                try:
                    data = channel.recv(4096)
                except Exception as exc:
                    if not self._closed.is_set():
                        self.closed.emit(str(exc))
                    return
                if not data:
                    self.closed.emit("终端连接已关闭")
                    return
                text = data.decode("utf-8", errors="replace")
                self._observe(text)
                self.output.emit(text)
        finally:
            self._closed.set()

    def _observe(self, text: str) -> None:
        for match in _OSC7_RE.finditer(text):
            path = unquote(match.group(1) or "")
            if path:
                self._update_cwd(path)
        with self._cwd_lock:
            deadline = self._pwd_probe_deadline
        if deadline and time.monotonic() < deadline:
            for line in text.splitlines():
                stripped = _strip_ansi(line).strip()
                if stripped.startswith("/") and " " not in stripped and "\t" not in stripped:
                    self._update_cwd(stripped)
                    with self._cwd_lock:
                        self._pwd_probe_deadline = 0.0
                    break

    def _update_cwd(self, path: str) -> None:
        cleaned = path.rstrip("\r\n").rstrip("/") or "/"
        with self._cwd_lock:
            if cleaned == self._cwd:
                return
            self._cwd = cleaned
        self.workingDirChanged.emit(cleaned)


_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)

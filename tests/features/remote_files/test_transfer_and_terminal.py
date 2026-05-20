from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QCoreApplication

from features.remote_files.terminal_session import RemoteTerminalBridge
from features.remote_files.transfer_service import RemoteTransferService


class FakeBackend:
    def __init__(self) -> None:
        self.uploads = []
        self.downloads = []

    def upload_file(self, local_path, remote_path, progress=None):
        self.uploads.append((local_path, remote_path))
        if progress is not None:
            progress(5, 10)
            progress(10, 10)

    def download_file(self, remote_path, local_path, progress=None):
        self.downloads.append((remote_path, local_path))
        Path(local_path).write_bytes(b"data")
        if progress is not None:
            progress(4, 4)


class FakeChannel:
    def __init__(self) -> None:
        self.sent = []
        self.resized = []
        self.closed = False
        self._chunks = [b"hello", b""]

    def send(self, text):
        self.sent.append(text)

    def resize_pty(self, width, height):
        self.resized.append((width, height))

    def recv(self, size):
        del size
        time.sleep(0.01)
        return self._chunks.pop(0)

    def close(self):
        self.closed = True


def test_transfer_service_reports_progress_and_completion(tmp_path: Path) -> None:
    backend = FakeBackend()
    updates = []
    messages = []
    service = RemoteTransferService(lambda: backend, on_transfers_updated=updates.append, on_message=messages.append)
    local = tmp_path / "file.txt"
    local.write_bytes(b"1234567890")

    service.start_upload(str(local), "/remote/file.txt")
    deadline = time.time() + 2
    while time.time() < deadline:
        latest = updates[-1][0] if updates and updates[-1] else {}
        if latest.get("status") == "completed":
            break
        time.sleep(0.02)

    service.close()

    assert updates[-1][0]["status"] == "completed"
    assert updates[-1][0]["progress"] == 100
    assert messages[-1] == "传输完成"
    assert backend.uploads == [(str(local), "/remote/file.txt")]


def test_terminal_bridge_sends_input_resize_and_output(qt_app) -> None:
    bridge = RemoteTerminalBridge()
    channel = FakeChannel()
    output = []
    closed = []
    bridge.output.connect(output.append)
    bridge.closed.connect(closed.append)

    bridge.attach(channel)
    bridge.sendInput("ls\r")
    bridge.resize(120, 32)

    deadline = time.time() + 2
    while time.time() < deadline and not closed:
        qt_app.processEvents()
        time.sleep(0.02)

    bridge.close()

    assert channel.sent == ["ls\r"]
    assert channel.resized == [(120, 32)]
    assert "hello" in output
    assert closed


def test_transfer_service_cancel_marks_item() -> None:
    backend = FakeBackend()
    updates = []
    service = RemoteTransferService(lambda: backend, on_transfers_updated=updates.append, on_message=lambda message: None)

    transfer_id = service.start_download("/remote/a.txt", "/tmp/a.txt", 100)
    service.cancel(transfer_id)
    service.close()

    assert any(item and item[0]["status"] == "cancelled" for item in updates if item)


import pytest


@pytest.fixture
def qt_app():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app

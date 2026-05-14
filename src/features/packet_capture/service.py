from __future__ import annotations

import random
from typing import Callable

from PySide6.QtCore import QObject, QTimer


class PacketCaptureService(QObject):
    def __init__(self, on_rows_updated: Callable[[list[dict]], None], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._on_rows_updated = on_rows_updated
        self._capture_running = False
        self._rows: list[dict] = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._append_mock_packet)

    def start(self) -> None:
        if self._capture_running:
            return
        self._capture_running = True
        self._timer.start(1200)

    def stop(self) -> None:
        self._capture_running = False
        self._timer.stop()

    def clear_rows(self) -> None:
        self._rows = []
        self._on_rows_updated(self._rows)

    def _append_mock_packet(self) -> None:
        if not self._capture_running:
            return
        methods = ["GET", "POST", "PUT", "DELETE"]
        paths = ["/api/users", "/api/login", "/api/order/12", "/api/system/ping", "/v1/files/upload"]
        status_codes = ["200", "201", "400", "401", "404", "500"]
        row = {
            "method": random.choice(methods),
            "path": random.choice(paths),
            "status": random.choice(status_codes),
            "size": f"{random.randint(1, 120)}KB",
        }
        self._rows = [row] + self._rows[:200]
        self._on_rows_updated(self._rows)

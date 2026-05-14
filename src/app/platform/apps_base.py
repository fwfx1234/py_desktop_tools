from __future__ import annotations

from typing import Protocol
from pathlib import Path

from .models import AppEntry


class AppIndexerProtocol(Protocol):
    def scan_apps(self, icon_dir: Path | None = None) -> list[AppEntry]:
        ...

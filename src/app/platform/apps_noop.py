from __future__ import annotations

from pathlib import Path

from .models import AppEntry


class NoopAppIndexer:
    def scan_apps(self, icon_dir: Path | None = None) -> list[AppEntry]:
        del icon_dir
        return []

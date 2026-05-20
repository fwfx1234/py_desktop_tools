from __future__ import annotations

from pathlib import Path

from app.platform.models import AppEntry


class NoopAppIndexer:
    def scan_apps(
        self,
        icon_dir: Path | None = None,
        *,
        extract_icons: bool = True,
    ) -> list[AppEntry]:
        del icon_dir, extract_icons
        return []

    def quick_signature(self) -> str:
        return "noop-apps-v1:0"

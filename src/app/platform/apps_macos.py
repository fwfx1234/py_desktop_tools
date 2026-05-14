from __future__ import annotations

import plistlib
from pathlib import Path

from .models import AppEntry

_APP_DIRS = [
    Path("/Applications"),
    Path.home() / "Applications",
    Path("/System/Applications"),
    Path("/Applications/Utilities"),
]


class MacOSAppIndexer:
    def scan_apps(self, icon_dir: Path | None = None) -> list[AppEntry]:
        del icon_dir
        seen: set[str] = set()
        apps: list[AppEntry] = []
        for root in _APP_DIRS:
            if not root.is_dir():
                continue
            for app_dir in root.rglob("*.app"):
                launch_path = str(app_dir.resolve())
                if launch_path in seen:
                    continue
                seen.add(launch_path)
                info = _read_info_plist(app_dir)
                name = (
                    str(info.get("CFBundleDisplayName") or "")
                    or str(info.get("CFBundleName") or "")
                    or app_dir.stem
                )
                bundle_id = str(info.get("CFBundleIdentifier") or "")
                apps.append(
                    AppEntry(
                        platform="macos",
                        name=name,
                        launch_path=launch_path,
                        bundle_id=bundle_id,
                    )
                )
        return apps


def _read_info_plist(app_dir: Path) -> dict:
    info_path = app_dir / "Contents" / "Info.plist"
    if not info_path.is_file():
        return {}
    try:
        with info_path.open("rb") as file_obj:
            raw = plistlib.load(file_obj)
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}

from __future__ import annotations

import sys

from .models import PlatformResult


class DefaultPermissionApi:
    def accessibility_status(self) -> PlatformResult:
        if sys.platform == "win32":
            return PlatformResult(True, data={"status": "not_required", "platform": "windows"})
        if sys.platform == "darwin":
            return PlatformResult(True, data={"status": "unknown", "platform": "macos"})
        return PlatformResult(False, "当前平台不支持", "unsupported", {"status": "unsupported"})

    def screen_recording_status(self) -> PlatformResult:
        if sys.platform == "win32":
            return PlatformResult(True, data={"status": "not_required", "platform": "windows"})
        if sys.platform == "darwin":
            return PlatformResult(True, data={"status": "unknown", "platform": "macos"})
        return PlatformResult(False, "当前平台不支持", "unsupported", {"status": "unsupported"})

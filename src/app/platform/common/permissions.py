from __future__ import annotations

import subprocess
import sys

from app.platform.models import PlatformResult


class DefaultPermissionApi:
    def accessibility_status(self) -> PlatformResult:
        if sys.platform == "win32":
            return PlatformResult(True, data={"status": "not_required", "platform": "windows"})
        if sys.platform == "darwin":
            return _macos_accessibility_status()
        return PlatformResult(False, "当前平台不支持", "unsupported", {"status": "unsupported"})

    def open_accessibility_settings(self) -> PlatformResult:
        if sys.platform != "darwin":
            return PlatformResult(False, "当前平台不支持", "unsupported")
        return _open_macos_accessibility_settings()

    def screen_recording_status(self) -> PlatformResult:
        if sys.platform == "win32":
            return PlatformResult(True, data={"status": "not_required", "platform": "windows"})
        if sys.platform == "darwin":
            return PlatformResult(True, data={"status": "unknown", "platform": "macos"})
        return PlatformResult(False, "当前平台不支持", "unsupported", {"status": "unsupported"})


def _macos_accessibility_status() -> PlatformResult:
    try:
        import ApplicationServices

        trusted = bool(ApplicationServices.AXIsProcessTrusted())
    except Exception as exc:
        return PlatformResult(False, "无法检测辅助功能权限", "check_failed", {"status": "unknown", "platform": "macos", "error": str(exc)})
    return PlatformResult(
        trusted,
        "已授权" if trusted else "未授权",
        "" if trusted else "not_authorized",
        {"status": "authorized" if trusted else "not_authorized", "platform": "macos"},
    )


def _open_macos_accessibility_settings() -> PlatformResult:
    try:
        _request_macos_accessibility_prompt()
        urls = [
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
            "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_Accessibility",
        ]
        for url in urls:
            subprocess.Popen(["open", url])
        return PlatformResult(True, "已打开系统设置", data={"urls": urls})
    except Exception as exc:
        return PlatformResult(False, "打开系统设置失败", "open_failed", {"error": str(exc)})


def _request_macos_accessibility_prompt() -> None:
    try:
        import ApplicationServices

        prompt_key = getattr(ApplicationServices, "kAXTrustedCheckOptionPrompt", "AXTrustedCheckOptionPrompt")
        request = getattr(ApplicationServices, "AXIsProcessTrustedWithOptions", None)
        if callable(request):
            request({prompt_key: True})
    except Exception:
        return

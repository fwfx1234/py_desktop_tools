from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from .models import AppEntry, PlatformResult


class WindowsExternalLauncher:
    def launch_app(self, app: AppEntry | dict) -> PlatformResult:
        launch_path = _launch_path_from_app(app)
        if not launch_path:
            return PlatformResult(False, "应用路径为空", "invalid")
        if not Path(launch_path).exists():
            return PlatformResult(False, "应用路径不存在", "not_found")
        try:
            os.startfile(launch_path)
            return PlatformResult(True, data={"launchPath": launch_path})
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")

    def launch_system_action(self, action: str) -> PlatformResult:
        try:
            subprocess.Popen(action, shell=True)
            return PlatformResult(True, data={"action": action})
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")

    def open_path(self, path: str | Path) -> PlatformResult:
        raw = str(path)
        if not Path(raw).exists():
            return PlatformResult(False, "路径不存在", "not_found")
        try:
            os.startfile(raw)
            return PlatformResult(True, data={"path": raw})
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")

    def reveal_in_file_manager(self, path: str | Path) -> PlatformResult:
        raw = str(path)
        if not Path(raw).exists():
            return PlatformResult(False, "路径不存在", "not_found")
        try:
            subprocess.Popen(["explorer.exe", "/select,", raw])
            return PlatformResult(True, data={"path": raw})
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")

    def open_url(self, url: str) -> PlatformResult:
        if QDesktopServices.openUrl(QUrl(url)):
            return PlatformResult(True, data={"url": url})
        return PlatformResult(False, "无法打开 URL", "failed")


class MacOSExternalLauncher:
    def launch_app(self, app: AppEntry | dict) -> PlatformResult:
        launch_path = _launch_path_from_app(app)
        if not launch_path:
            return PlatformResult(False, "应用路径为空", "invalid")
        if not Path(launch_path).exists():
            return PlatformResult(False, "应用路径不存在", "not_found")
        try:
            subprocess.Popen(["open", launch_path])
            return PlatformResult(True, data={"launchPath": launch_path})
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")

    def launch_system_action(self, action: str) -> PlatformResult:
        try:
            subprocess.Popen(action, shell=True)
            return PlatformResult(True, data={"action": action})
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")

    def open_path(self, path: str | Path) -> PlatformResult:
        raw = str(path)
        if not Path(raw).exists():
            return PlatformResult(False, "路径不存在", "not_found")
        try:
            subprocess.Popen(["open", raw])
            return PlatformResult(True, data={"path": raw})
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")

    def reveal_in_file_manager(self, path: str | Path) -> PlatformResult:
        raw = str(path)
        if not Path(raw).exists():
            return PlatformResult(False, "路径不存在", "not_found")
        try:
            subprocess.Popen(["open", "-R", raw])
            return PlatformResult(True, data={"path": raw})
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")

    def open_url(self, url: str) -> PlatformResult:
        if QDesktopServices.openUrl(QUrl(url)):
            return PlatformResult(True, data={"url": url})
        return PlatformResult(False, "无法打开 URL", "failed")


class NoopExternalLauncher:
    def launch_app(self, app: AppEntry | dict) -> PlatformResult:
        del app
        return PlatformResult(False, "当前平台不支持", "unsupported")

    def launch_system_action(self, action: str) -> PlatformResult:
        del action
        return PlatformResult(False, "当前平台不支持", "unsupported")

    def open_path(self, path: str | Path) -> PlatformResult:
        del path
        return PlatformResult(False, "当前平台不支持", "unsupported")

    def reveal_in_file_manager(self, path: str | Path) -> PlatformResult:
        del path
        return PlatformResult(False, "当前平台不支持", "unsupported")

    def open_url(self, url: str) -> PlatformResult:
        del url
        return PlatformResult(False, "当前平台不支持", "unsupported")


def _launch_path_from_app(app: AppEntry | dict) -> str:
    if isinstance(app, AppEntry):
        return app.launch_path
    return str(app.get("launchPath") or app.get("lnkPath") or app.get("launch_path") or "")

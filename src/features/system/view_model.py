from __future__ import annotations

from weakref import ref

from PySide6.QtCore import QObject, Property, Signal, Slot

from app.paths import data_dir
from app.plugins.manifest_loader import load_all_plugin_manifests


class SystemSettingsViewModel(QObject):
    appIndexChanged = Signal()
    permissionsChanged = Signal()

    def __init__(self, command_service: object | None = None, permissions: object | None = None) -> None:
        super().__init__()
        self._command_service = command_service
        self._permissions = permissions
        self._disposed = False
        if command_service is not None:
            on_completed = getattr(command_service, "on_app_scan_completed", None)
            if callable(on_completed):
                self_ref = ref(self)

                def notify() -> None:
                    obj = self_ref()
                    if obj is not None and not obj._disposed:
                        obj.appIndexChanged.emit()

                on_completed(notify)

    @Property(bool, notify=appIndexChanged)
    def appScanRunning(self) -> bool:
        if self._command_service is None:
            return False
        return bool(getattr(self._command_service, "app_scan_running", False))

    @Property(int, notify=appIndexChanged)
    def appCount(self) -> int:
        if self._command_service is None:
            return 0
        count_apps = getattr(self._command_service, "count_apps", None)
        if not callable(count_apps):
            return 0
        try:
            return int(count_apps())
        except Exception:
            return 0

    @Slot(result="QVariantMap")
    def diagnostics(self) -> dict:
        manifests = load_all_plugin_manifests()
        background = [item.id for item in manifests if item.activation == "background"]
        root = data_dir()
        return {
            "dataDir": str(root),
            "logDir": str(root / "logs"),
            "pluginCount": len(manifests),
            "backgroundPlugins": ", ".join(background) if background else "无",
        }

    @Property(str, notify=permissionsChanged)
    def accessibilityStatusText(self) -> str:
        status = self._accessibility_status()
        code = str(status.get("status") or "unknown")
        if code == "authorized":
            return "辅助功能权限：已授权"
        if code == "not_authorized":
            return "辅助功能权限：未授权"
        if code == "not_required":
            return "辅助功能权限：无需授权"
        return "辅助功能权限：未知"

    @Property(bool, notify=permissionsChanged)
    def accessibilityAuthorized(self) -> bool:
        return str(self._accessibility_status().get("status") or "") in {"authorized", "not_required"}

    @Slot()
    def refreshPermissions(self) -> None:
        self.permissionsChanged.emit()

    @Slot(result=bool)
    def openAccessibilitySettings(self) -> bool:
        if self._permissions is None:
            return False
        open_settings = getattr(self._permissions, "open_accessibility_settings", None)
        if not callable(open_settings):
            return False
        try:
            result = open_settings()
        except Exception:
            return False
        self.permissionsChanged.emit()
        return bool(getattr(result, "ok", False))

    @Slot(result=bool)
    def rescanApplications(self) -> bool:
        if self._command_service is None:
            return False
        start = getattr(self._command_service, "start_app_scan", None)
        if not callable(start):
            return False
        started = bool(start(force=True))
        self.appIndexChanged.emit()
        return started

    def dispose(self) -> None:
        self._disposed = True

    def _accessibility_status(self) -> dict:
        if self._permissions is None:
            return {"status": "unknown"}
        status_fn = getattr(self._permissions, "accessibility_status", None)
        if not callable(status_fn):
            return {"status": "unknown"}
        try:
            result = status_fn()
        except Exception:
            return {"status": "unknown"}
        data = getattr(result, "data", None)
        return data if isinstance(data, dict) else {"status": "unknown"}

from __future__ import annotations

from pathlib import Path
from weakref import ref

from PySide6.QtCore import QObject, Property, Signal, Slot

from app.paths import data_dir
from app.platform.models import PlatformResult
from app.plugins.manifest_loader import load_all_plugin_manifests


class SystemSettingsViewModel(QObject):
    appIndexChanged = Signal()
    permissionsChanged = Signal()
    pluginImportChanged = Signal()
    pluginImportFinished = Signal(bool, str)

    def __init__(
        self,
        command_service: object | None = None,
        permissions: object | None = None,
        plugin_importer: object | None = None,
        imported_plugin_root: object | None = None,
        file_manager: object | None = None,
    ) -> None:
        super().__init__()
        self._command_service = command_service
        self._permissions = permissions
        self._plugin_importer = plugin_importer
        self._imported_plugin_root = imported_plugin_root
        self._file_manager = file_manager
        self._last_plugin_import_message = "支持导入插件目录或 .zip 插件包"
        self._last_plugin_import_ok = False
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

    @Property(str, notify=pluginImportChanged)
    def pluginImportMessage(self) -> str:
        return self._last_plugin_import_message

    @Property(bool, notify=pluginImportChanged)
    def pluginImportOk(self) -> bool:
        return self._last_plugin_import_ok

    @Property(str, notify=pluginImportChanged)
    def importedPluginRoot(self) -> str:
        root = self._resolve_imported_plugin_root()
        return str(root) if root is not None else ""

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

    @Slot(str, result="QVariantMap")
    def importPlugin(self, source: str) -> dict:
        importer = self._plugin_importer
        if not callable(importer):
            return self._set_plugin_import_result(False, "插件导入服务不可用", "unavailable")
        try:
            result = importer(source)
        except Exception as exc:
            return self._set_plugin_import_result(False, f"导入失败: {exc}", "failed")
        if not isinstance(result, dict):
            return self._set_plugin_import_result(False, "插件导入服务返回异常", "invalid_result")
        ok = bool(result.get("ok"))
        message = str(result.get("message") or ("导入完成" if ok else "导入失败"))
        self._last_plugin_import_ok = ok
        self._last_plugin_import_message = message
        self.pluginImportChanged.emit()
        self.pluginImportFinished.emit(ok, message)
        return result

    @Slot(result=bool)
    def openImportedPluginRoot(self) -> bool:
        root = self._resolve_imported_plugin_root()
        if root is None:
            self._set_plugin_import_result(False, "插件导入目录不可用", "root_unavailable")
            return False
        try:
            root.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self._set_plugin_import_result(False, f"无法访问插件目录: {exc}", "root_failed")
            return False
        reveal = getattr(self._file_manager, "reveal_in_file_manager", None)
        open_path = getattr(self._file_manager, "open_path", None)
        for action in (open_path, reveal):
            if not callable(action):
                continue
            try:
                result = action(root)
            except Exception:
                continue
            if isinstance(result, PlatformResult):
                if result.ok:
                    self._set_plugin_import_result(True, f"已打开插件目录: {root}", "root_opened")
                    return True
            elif bool(result):
                self._set_plugin_import_result(True, f"已打开插件目录: {root}", "root_opened")
                return True
        self._set_plugin_import_result(False, "打开插件目录失败", "root_open_failed")
        return False

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

    def _set_plugin_import_result(self, ok: bool, message: str, code: str) -> dict:
        self._last_plugin_import_ok = ok
        self._last_plugin_import_message = message
        self.pluginImportChanged.emit()
        self.pluginImportFinished.emit(ok, message)
        return {
            "ok": ok,
            "message": message,
            "code": code,
            "pluginIds": [],
            "targetDir": "",
        }

    def _resolve_imported_plugin_root(self) -> Path | None:
        root = self._imported_plugin_root
        if callable(root):
            try:
                value = root()
            except Exception:
                return None
        else:
            value = root
        if value is None:
            return None
        try:
            return Path(value)
        except TypeError:
            return None

from __future__ import annotations

from app.plugins.manifest import PluginManifest
from app.plugins.runtime import PluginAction, PluginContext


def _log():
    from app.logging import get_logger

    return get_logger("features.app_launcher.runtime")


class AppLauncherListSession:
    """List-template session for launching system applications."""

    def __init__(
        self,
        manifest: PluginManifest,
        command_index: object,
        platform: object,
        command_service: object | None = None,
    ) -> None:
        self.manifest = manifest
        self.launch_mode = "list"
        self._command_index = command_index
        self._platform = platform
        self._command_service = command_service
        self._query = ""
        self._start_scan()

    def create_qml_context(self) -> dict:
        return {}

    def qml_page(self) -> str:
        return ""

    def list_model(self) -> list[dict]:
        apps = self._search_apps(self._query, limit=50)
        if apps:
            return [self._to_list_item(app) for app in apps]
        if self._scan_running():
            return [self._status_item("正在索引应用", "应用列表和图标会在后台写入缓存", "qta:mdi6.progress-clock")]
        if self._count_apps() > 0:
            return [self._status_item("暂无匹配应用", "换个关键词或清空搜索", "qta:mdi6.magnify-close")]
        return [self._status_item("暂无应用缓存", "正在准备后台索引", "qta:mdi6.database-search-outline")]

    def on_input_changed(self, text: str) -> list[dict]:
        self._query = text
        return self.list_model()

    def on_list_item_selected(self, item_id: str) -> None:
        if item_id.startswith("__"):
            self._start_scan(force=True)
            return
        app = self._find_app(item_id)
        if not app:
            return
        launch_path = str(app.get("launchPath") or "")
        if launch_path:
            self._command_index.record_launch_by_app_path(launch_path)
            result = self._platform.launch_application(app)
            if not result.ok:
                _log().warning("app.launch_failed", "应用启动失败", code=result.code, message=result.message, launchPath=launch_path)

    def on_list_item_action(self, item_id: str, action_id: str) -> list[dict]:
        del item_id
        if action_id == "rescan":
            self._rescan()
        return self.list_model()

    def close(self) -> None:
        return

    def _start_scan(self, *, force: bool = False) -> None:
        if self._command_service is not None:
            start = getattr(self._command_service, "start_app_scan", None)
            if callable(start):
                start(force=force)
                return
        if force or self._command_index.count_apps() == 0:
            apps = self._platform.scan_applications(extract_icons=False)
            self._command_index.sync_apps([app.to_db_dict() for app in apps])

    def _rescan(self) -> None:
        self._start_scan(force=True)

    def _find_app(self, item_id: str) -> dict | None:
        for app in self._search_apps(self._query, limit=100):
            if str(app.get("id")) == item_id:
                return app
        return None

    def _search_apps(self, query: str, *, limit: int) -> list[dict]:
        if self._command_service is not None:
            search = getattr(self._command_service, "search_apps", None)
            if callable(search):
                return list(search(query, limit=limit))
        return self._command_index.search_apps(query, limit=limit)

    def _scan_running(self) -> bool:
        if self._command_service is None:
            return False
        return bool(getattr(self._command_service, "app_scan_running", False))

    def _count_apps(self) -> int:
        if self._command_service is not None:
            count_apps = getattr(self._command_service, "count_apps", None)
            if callable(count_apps):
                return int(count_apps())
        return int(self._command_index.count_apps())

    @staticmethod
    def _to_list_item(app: dict) -> dict:
        icon_path = app.get("iconPath", "")
        icon = (
            "file:///" + str(icon_path).replace("\\", "/")
            if icon_path
            else "qta:mdi6.application-outline"
        )
        return {
            "id": str(app.get("id", "")),
            "title": str(app.get("name", "")),
            "subtitle": str(app.get("launchPath") or ""),
            "icon": icon,
            "payload": {"launchPath": app.get("launchPath") or ""},
        }

    @staticmethod
    def _status_item(title: str, subtitle: str, icon: str) -> dict:
        return {
            "id": "__app_index_status__",
            "title": title,
            "subtitle": subtitle,
            "icon": icon,
            "enabled": False,
            "payload": {},
        }


class AppLauncherRuntime:
    def on_enter(self, ctx: PluginContext, action: PluginAction) -> AppLauncherListSession:
        if ctx.command_index is None:
            raise RuntimeError("Command index is unavailable")
        platform = ctx.platform or ctx.services.platform
        if platform is None:
            raise RuntimeError("Platform API is unavailable")
        return AppLauncherListSession(
            action.manifest,
            ctx.command_index,
            platform,
            ctx.command_service,
        )

    def on_exit(self) -> None:
        return


def create_runtime() -> AppLauncherRuntime:
    return AppLauncherRuntime()

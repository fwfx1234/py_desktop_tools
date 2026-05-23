from __future__ import annotations

from time import perf_counter

from PySide6.QtCore import QObject, Property, Signal, Slot

from app.logging import get_logger, make_trace_id
from app.commands.context import build_launcher_context
from app.commands.command_service import CommandService
from app.plugins.service_registry import ServiceRegistry


class LauncherBridge(QObject):
    """QML bridge for global search, command launch, and plugin input.

    The object is the only QML-facing gateway for launcher search and launch.
    """

    searchCompleted = Signal()
    pluginLaunched = Signal(str)
    pluginCommandLaunched = Signal(str, str, str, "QVariantMap")
    pluginClosed = Signal(str)
    pluginSuspended = Signal(str, str)
    pluginInputChanged = Signal()
    pluginInputEdited = Signal(str, str)
    pluginListChanged = Signal()
    pluginListItemActivated = Signal(str, str)
    pluginListItemActionActivated = Signal(str, str, str)
    pluginDetachedToWindow = Signal(str)
    retainedPluginExpired = Signal(str)
    restartRequested = Signal()
    systemCommandRun = Signal(str, str)
    hideLauncherRequested = Signal()
    appIndexChanged = Signal()
    _appIndexScanCompleted = Signal()

    def __init__(
        self,
        command_service: CommandService,
        services: ServiceRegistry | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._command_service = command_service
        self._services = services or ServiceRegistry()
        self._results: list[dict] = []
        self._plugin_list_items: list[dict] = []
        self._plugin_input = ""
        self._last_query = ""
        self._log = get_logger("app.launcher.bridge")
        self._trace_id = ""
        self._appIndexScanCompleted.connect(self._refresh_after_app_scan)
        self._command_service.on_app_scan_completed(self._appIndexScanCompleted.emit)

    @Property("QVariantList", notify=searchCompleted)
    def searchResults(self) -> list[dict]:
        return self._results

    @Property("QVariantList", notify=searchCompleted)
    def allPlugins(self) -> list[dict]:
        return self._command_service.all_plugin_items()

    @Property(str, notify=pluginInputChanged)
    def pluginInput(self) -> str:
        return self._plugin_input

    @Property("QVariantList", notify=pluginListChanged)
    def pluginListItems(self) -> list[dict]:
        return self._plugin_list_items

    @Slot(str)
    def performSearch(self, query: str) -> None:
        started_at = perf_counter()
        self._last_query = query
        self._trace_id = make_trace_id()
        context = build_launcher_context(
            query,
            self._command_service.known_prefixes(),
            self._latest_clipboard_item(),
        )
        self._results = self._command_service.search(query, context)
        elapsed_ms = int((perf_counter() - started_at) * 1000)
        log_search = self._log.warning if elapsed_ms >= 120 else self._log.debug
        log_search(
            "launcher.search",
            "执行搜索",
            traceId=self._trace_id,
            queryLength=len(query or ""),
            resultCount=len(self._results),
            elapsedMs=elapsed_ms,
        )
        self.searchCompleted.emit()

    @Slot()
    def _refresh_after_app_scan(self) -> None:
        self.performSearch(self._last_query)
        self.appIndexChanged.emit()

    @Slot(str)
    def launchPlugin(self, plugin_id: str) -> None:
        self._record_plugin_launch(plugin_id)
        self._log.debug("launcher.plugin_launch", "启动插件", pluginId=plugin_id, traceId=self._trace_id)
        self.pluginLaunched.emit(plugin_id)
        self.pluginCommandLaunched.emit(plugin_id, "", "", {"_traceId": self._trace_id})

    @Slot(str, str)
    def launchItem(self, item_id: str, source: str) -> None:
        if source == "plugin":
            item = self._find_result(item_id) or {}
            self._record_item_launch(item)
            plugin_id = str(item.get("pluginId") or item_id)
            command_id = str(item.get("commandId") or "")
            payload = item.get("payload", {})
            input_text = str(item["inputText"]) if "inputText" in item else ""
            launch_payload = payload.copy() if isinstance(payload, dict) else {}
            launch_payload["clearLauncherInputOnEnter"] = bool(
                item.get("clearInputOnEnter")
            )
            self._log.debug(
                "launcher.plugin_item_launch",
                "启动插件命令",
                pluginId=plugin_id,
                commandId=command_id,
                traceId=self._trace_id,
            )
            launch_payload["_traceId"] = self._trace_id
            self.pluginLaunched.emit(plugin_id)
            self.pluginCommandLaunched.emit(
                plugin_id,
                command_id,
                input_text,
                launch_payload,
            )
            return

        try:
            item = self._find_result(item_id)
            payload = item.get("payload", {}) if item else {}
            if source == "system" and payload.get("action") == "__restart_app__":
                self._record_item_launch(item or {})
                self._log.debug("launcher.restart", "请求重启应用", traceId=self._trace_id)
                self.restartRequested.emit()
                return
            launched_name = self._command_service.launch_external_item(
                item_id,
                source,
                payload,
            )
            if launched_name:
                self.systemCommandRun.emit(item_id, launched_name)
        except Exception as exc:
            self._log.error("launcher.item_launch_failed", "启动项目失败", itemId=item_id, source=source, traceId=self._trace_id, error=str(exc))

    @Slot(str, str, str)
    def launchItemWithInput(self, item_id: str, source: str, input_text: str) -> None:
        if source != "plugin":
            self.launchItem(item_id, source)
            return
        item = self._find_result(item_id) or {}
        self._record_item_launch(item)
        plugin_id = str(item.get("pluginId") or item_id)
        command_id = str(item.get("commandId") or "")
        payload = item.get("payload", {})
        effective_input = str(item["inputText"]) if "inputText" in item else input_text
        launch_payload = payload.copy() if isinstance(payload, dict) else {}
        launch_payload["clearLauncherInputOnEnter"] = bool(
            item.get("clearInputOnEnter")
        )
        launch_payload["_traceId"] = self._trace_id
        self.pluginLaunched.emit(plugin_id)
        self.pluginCommandLaunched.emit(
            plugin_id,
            command_id,
            effective_input,
            launch_payload,
        )

    @Slot(str, str)
    def setPluginInput(self, plugin_id: str, text: str) -> None:
        if self._plugin_input != text:
            self._plugin_input = text
            self.pluginInputChanged.emit()
        self._log.debug("launcher.plugin_input", "插件输入变更", pluginId=plugin_id, textLength=len(text or ""))
        self.pluginInputEdited.emit(plugin_id, text)

    @Slot(str, str)
    def suspendPlugin(self, plugin_id: str, host: str) -> None:
        if plugin_id:
            self.setPluginListItems([])
            self._log.debug("launcher.plugin_suspend", "挂起插件", pluginId=plugin_id, host=host, traceId=self._trace_id)
            self.pluginSuspended.emit(plugin_id, host)

    @Slot(str)
    def closePlugin(self, plugin_id: str) -> None:
        if plugin_id:
            self._log.debug("launcher.plugin_close", "关闭插件", pluginId=plugin_id, traceId=self._trace_id)
            self.pluginClosed.emit(plugin_id)

    @Slot(str)
    def detachPluginToWindow(self, plugin_id: str) -> None:
        if plugin_id:
            self._log.debug("launcher.plugin_detach", "插件脱离到窗口", pluginId=plugin_id, traceId=self._trace_id)
            self.pluginDetachedToWindow.emit(plugin_id)

    @Slot(str, str)
    def activatePluginListItem(self, plugin_id: str, item_id: str) -> None:
        self.pluginListItemActivated.emit(plugin_id, item_id)

    @Slot()
    def hideLauncher(self) -> None:
        self.hideLauncherRequested.emit()

    @Slot()
    def checkAppIndex(self) -> None:
        self._command_service.check_app_index_changes()

    @Slot()
    def refreshPlugins(self) -> None:
        self.performSearch(self._last_query)

    @Slot(str, str, str)
    def activatePluginListItemAction(
        self,
        plugin_id: str,
        item_id: str,
        action_id: str,
    ) -> None:
        self.pluginListItemActionActivated.emit(plugin_id, item_id, action_id)

    def setPluginListItems(self, items: list[dict]) -> None:
        self._plugin_list_items = items
        self.pluginListChanged.emit()

    def _find_result(self, item_id: str) -> dict | None:
        for item in self._results:
            if item.get("id") == item_id:
                return item
        return None

    def _record_plugin_launch(self, plugin_id: str) -> None:
        try:
            self._command_service.record_plugin_launch(plugin_id)
        except Exception as exc:
            self._log.warning("launcher.usage_record_failed", "记录插件启动次数失败", pluginId=plugin_id, traceId=self._trace_id, error=str(exc))

    def _record_item_launch(self, item: dict) -> None:
        try:
            self._command_service.record_item_launch(item)
        except Exception as exc:
            self._log.warning(
                "launcher.usage_record_failed",
                "记录启动项使用次数失败",
                itemId=str(item.get("id") or ""),
                traceId=self._trace_id,
                error=str(exc),
            )

    def _latest_clipboard_item(self) -> dict | None:
        service = self._services.clipboard
        latest_item = getattr(service, "latest_context_item", None)
        if not callable(latest_item):
            return None
        try:
            item = latest_item()
        except Exception as exc:
            self._log.warning("launcher.clipboard_latest_failed", "读取最新剪贴板记录失败", error=str(exc), traceId=self._trace_id)
            return None
        return item if isinstance(item, dict) else None

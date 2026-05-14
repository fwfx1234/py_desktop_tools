from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from app.commands.context import build_launcher_context
from app.commands.command_service import CommandService


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

    def __init__(
        self,
        command_service: CommandService,
        services: dict[str, object] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._command_service = command_service
        self._services = services if services is not None else {}
        self._results: list[dict] = []
        self._plugin_list_items: list[dict] = []
        self._plugin_input = ""

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
        context = build_launcher_context(
            query,
            self._command_service.known_prefixes(),
            self._latest_clipboard_item(),
        )
        self._results = self._command_service.search(query, context)
        self.searchCompleted.emit()

    @Slot(str)
    def launchPlugin(self, plugin_id: str) -> None:
        self._command_service.record_plugin_launch(plugin_id)
        self.pluginLaunched.emit(plugin_id)
        self.pluginCommandLaunched.emit(plugin_id, "", "", {})

    @Slot(str, str)
    def launchItem(self, item_id: str, source: str) -> None:
        if source == "plugin":
            item = self._find_result(item_id) or {}
            self._command_service.record_item_launch(item)
            plugin_id = str(item.get("pluginId") or item_id)
            command_id = str(item.get("commandId") or "")
            payload = item.get("payload", {})
            input_text = str(item["inputText"]) if "inputText" in item else ""
            launch_payload = payload.copy() if isinstance(payload, dict) else {}
            launch_payload["clearLauncherInputOnEnter"] = bool(
                item.get("clearInputOnEnter")
            )
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
                self._command_service.record_item_launch(item or {})
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
            print(f"[ERROR] 启动项目失败: {item_id} ({source}) - {exc}")

    @Slot(str, str, str)
    def launchItemWithInput(self, item_id: str, source: str, input_text: str) -> None:
        if source != "plugin":
            self.launchItem(item_id, source)
            return
        item = self._find_result(item_id) or {}
        self._command_service.record_item_launch(item)
        plugin_id = str(item.get("pluginId") or item_id)
        command_id = str(item.get("commandId") or "")
        payload = item.get("payload", {})
        effective_input = str(item["inputText"]) if "inputText" in item else input_text
        launch_payload = payload.copy() if isinstance(payload, dict) else {}
        launch_payload["clearLauncherInputOnEnter"] = bool(
            item.get("clearInputOnEnter")
        )
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
        self.pluginInputEdited.emit(plugin_id, text)

    @Slot(str, str)
    def suspendPlugin(self, plugin_id: str, host: str) -> None:
        if plugin_id:
            self.setPluginListItems([])
            self.pluginSuspended.emit(plugin_id, host)

    @Slot(str)
    def closePlugin(self, plugin_id: str) -> None:
        if plugin_id:
            self.pluginClosed.emit(plugin_id)

    @Slot(str)
    def detachPluginToWindow(self, plugin_id: str) -> None:
        if plugin_id:
            self.pluginDetachedToWindow.emit(plugin_id)

    @Slot(str, str)
    def activatePluginListItem(self, plugin_id: str, item_id: str) -> None:
        self.pluginListItemActivated.emit(plugin_id, item_id)

    @Slot()
    def hideLauncher(self) -> None:
        self.hideLauncherRequested.emit()

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

    def _latest_clipboard_item(self) -> dict | None:
        service = self._services.get("clipboard.background")
        store = getattr(service, "store", None)
        latest_item = getattr(store, "latest_captured_item", None)
        if not callable(latest_item):
            latest_item = getattr(store, "latest_item", None)
        if not callable(latest_item):
            return None
        try:
            item = latest_item()
        except Exception as exc:
            print(f"[WARN] 读取最新剪切板记录失败: {exc}")
            return None
        return item if isinstance(item, dict) else None

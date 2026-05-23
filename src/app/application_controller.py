from __future__ import annotations

from collections.abc import Callable
from time import perf_counter

from PySide6.QtCore import QTimer

from app.app_relauncher import restart_current_app
from app.launcher.launcher_window import LauncherWindowController
from app.logging import get_logger
from app.plugins.launch_request import PluginLaunchRequest
from app.plugins.manifest import PluginManifest
from app.plugins.session_manager import PluginSessionManager, SessionState


class ApplicationController:
    def __init__(
        self,
        *,
        session_manager: PluginSessionManager,
        plugin_host: object,
        launcher_bridge: object,
        launcher_window_controller: LauncherWindowController,
        on_quit: Callable[[], None],
    ) -> None:
        self._session_manager = session_manager
        self._plugin_host = plugin_host
        self._bridge = launcher_bridge
        self._launcher_window_controller = launcher_window_controller
        self._on_quit = on_quit
        self._log = get_logger("app.application_controller")
        self._last_clipboard_open_at = 0.0

    def connect(self) -> None:
        self._bridge.pluginCommandLaunched.connect(self.open_plugin)
        self._bridge.pluginClosed.connect(self.force_close_plugin)
        self._bridge.pluginSuspended.connect(self.suspend_plugin)
        self._bridge.pluginDetachedToWindow.connect(self.detach_plugin_to_window)
        self._bridge.pluginInputEdited.connect(self.on_plugin_input_edited)
        self._bridge.pluginListItemActivated.connect(self.on_plugin_list_item_activated)
        self._bridge.pluginListItemActionActivated.connect(self.on_plugin_list_item_action)
        self._bridge.restartRequested.connect(self.restart_app)
        self._bridge.hideLauncherRequested.connect(self.hide_launcher)
        self._bridge.appIndexChanged.connect(self.refresh_app_launcher_list)

    def refresh_manifests(self, manifests: list[PluginManifest]) -> None:
        refresh_plugins = getattr(self._bridge, "refreshPlugins", None)
        if callable(refresh_plugins):
            refresh_plugins()
        self.refresh_app_launcher_list()

    def toggle_launcher(self) -> None:
        signal_at = perf_counter()
        if not self._launcher_window_controller.is_available():
            self._log.warning("launcher.toggle_failed", "启动器窗口不存在或已销毁")
            return
        state_started_at = perf_counter()
        before = self._launcher_window_controller.snapshot()
        self._log.debug(
            "launcher.toggle_begin",
            "准备切换启动器窗口",
            visible=before["visible"],
            active=before["active"],
            width=before["width"],
            height=before["height"],
            stateElapsedMs=int((perf_counter() - state_started_at) * 1000),
        )
        if self._launcher_window_controller.is_visible():
            hide_started_at = perf_counter()
            self._launcher_window_controller.hide()
            self._log.debug("launcher.hidden_by_hotkey", "启动器已由热键隐藏", elapsedMs=int((perf_counter() - hide_started_at) * 1000))
            return
        self._launcher_window_controller.restore_state()
        show_result = self._launcher_window_controller.show(activate=True)
        check_app_index = getattr(self._bridge, "checkAppIndex", None)
        if callable(check_app_index):
            check_app_index()
        elapsed_ms = show_result["elapsedMs"]
        log_show = self._log.warning if elapsed_ms >= 120 else self._log.debug
        after = self._launcher_window_controller.snapshot()
        log_show(
            "launcher.show_requested",
            "已请求显示并激活启动器窗口",
            visible=after["visible"],
            active=after["active"],
            x=after["x"],
            y=after["y"],
            centerElapsedMs=show_result["centerElapsedMs"],
            showCallElapsedMs=show_result["showCallElapsedMs"],
            raiseElapsedMs=show_result["raiseElapsedMs"],
            activateElapsedMs=show_result["activateElapsedMs"],
            fromSignalMs=int((perf_counter() - signal_at) * 1000),
            elapsedMs=elapsed_ms,
        )
        QTimer.singleShot(50, lambda started_at=signal_at: self._launcher_window_controller.activate_and_log("launcher.state_after_show_50ms", started_at))

    def prewarm_launcher_window(self) -> None:
        self._launcher_window_controller.prewarm()

    def hide_launcher(self) -> None:
        self._launcher_window_controller.hide()

    def open_clipboard_history(self) -> None:
        now = perf_counter()
        if now - self._last_clipboard_open_at < 0.35:
            self._log.debug(
                "hotkey.clipboard_debounced",
                "剪贴板热键重复触发已忽略",
                sinceLastMs=int((now - self._last_clipboard_open_at) * 1000),
            )
            return
        self._last_clipboard_open_at = now
        self.open_plugin("clipboard", "", "", {"openInWindow": True})

    def open_plugin(
        self,
        plugin_id: str,
        command_id: str = "",
        input_text: str = "",
        payload: dict | None = None,
    ) -> None:
        payload = dict(payload or {})
        request = PluginLaunchRequest(
            plugin_id=plugin_id,
            command_id=command_id,
            input_text=input_text,
            payload=payload,
            preferred_host="window" if payload.get("openInWindow") else None,
        )
        self.open_plugin_request(request)

    def open_plugin_request(self, request: PluginLaunchRequest) -> None:
        if self._session_manager.has_session(request.plugin_id) and not self._session_manager.can_reuse_request(request):
            self._prepare_for_recreate(request)

        session = self._session_manager.open_request(request)
        if session is None:
            return

        shown = self._plugin_host.show(request, session)
        if not shown:
            self._session_manager.unload_plugin(request.plugin_id)
            return
        if session.launch_mode == "none":
            self._session_manager.unload_plugin(request.plugin_id)

    def suspend_plugin(self, plugin_id: str, host: str) -> None:
        if not plugin_id:
            return
        normalized_host = "window" if host == "window" else "list" if host == "list" else "inline"
        self._plugin_host.suspend(plugin_id, normalized_host)
        self._session_manager.suspend_plugin(plugin_id, normalized_host)

    def on_surface_retained_close(self, plugin_id: str, host: str) -> None:
        self._session_manager.suspend_plugin(plugin_id, "window" if host == "window" else "inline")

    def on_retention_expired(self, plugin_id: str, state: SessionState) -> None:
        self._plugin_host.notify_retention_expired(plugin_id, state)
        self._session_manager.unload_plugin(plugin_id)

    def detach_plugin_to_window(self, plugin_id: str) -> None:
        if not plugin_id:
            return
        request = PluginLaunchRequest(
            plugin_id=plugin_id,
            payload={"openInWindow": True},
            preferred_host="window",
        )
        session = self._session_manager.open_request(request)
        if session is None:
            return
        self._launcher_window_controller.detach_inline_plugin(plugin_id)
        shown = self._plugin_host.show(request, session)
        if not shown:
            self._session_manager.unload_plugin(plugin_id)

    def force_close_plugin(self, plugin_id: str) -> None:
        if plugin_id:
            self._plugin_host.destroy(plugin_id)
            self._session_manager.unload_plugin(plugin_id)

    def on_plugin_input_edited(self, plugin_id: str, text: str) -> None:
        items = self._session_manager.update_plugin_input(plugin_id, text)
        if self._session_manager.plugin_launch_mode(plugin_id) == "list":
            self._bridge.setPluginListItems(items)

    def on_plugin_list_item_activated(self, plugin_id: str, item_id: str) -> None:
        items = self._session_manager.activate_list_item(plugin_id, item_id)
        self._bridge.setPluginListItems(items)

    def on_plugin_list_item_action(self, plugin_id: str, item_id: str, action_id: str) -> None:
        items = self._session_manager.activate_list_item_action(plugin_id, item_id, action_id)
        self._bridge.setPluginListItems(items)

    def refresh_app_launcher_list(self) -> None:
        plugin_id, plugin_mode = self._launcher_window_controller.current_mixed_plugin()
        if plugin_id:
            if plugin_id != "app-launcher" or plugin_mode != "list":
                return
        items = self._session_manager.list_items("app-launcher")
        if items:
            self._bridge.setPluginListItems(items)

    def restart_app(self) -> None:
        restart_current_app()
        self._on_quit()

    def _prepare_for_recreate(self, request: PluginLaunchRequest) -> None:
        state = self._session_manager.get_session_state(request.plugin_id)
        if state is not None:
            self.on_retention_expired(request.plugin_id, state)
        if (
            request.payload.get("clearLauncherInputOnEnter")
        ):
            self._launcher_window_controller.set_search_input_silently("")


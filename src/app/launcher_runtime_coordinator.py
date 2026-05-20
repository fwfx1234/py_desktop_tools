from __future__ import annotations

from collections.abc import Callable
from time import perf_counter

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCursor

from app.app_relauncher import restart_current_app
from app.hotkey_coordinator import HotkeyCoordinator
from app.logging import get_logger
from app.platform.services import PlatformServices
from app.plugin_surface_coordinator import focused_window_point, is_qobject_alive
from app.plugins.background_manager import BackgroundManager
from app.plugins.launch_request import PluginLaunchRequest
from app.plugins.manifest import PluginManifest
from app.plugins.runtime import PluginContext
from app.plugins.session_manager import PluginSessionManager, SessionState


def _center_window_once(win: object, screen: object, width: int, height: int) -> None:
    if screen is None or not is_qobject_alive(win):
        return
    geometry = screen.availableGeometry()
    x = geometry.x() + max(0, (geometry.width() - width) // 2)
    y = geometry.y() + max(0, (geometry.height() - height) // 2)
    win.setX(x)
    win.setY(y)


def _set_window_screen(win: object, screen: object) -> None:
    if screen is None or not is_qobject_alive(win):
        return
    set_screen = getattr(win, "setScreen", None)
    if callable(set_screen):
        try:
            set_screen(screen)
        except RuntimeError:
            return


class LauncherRuntimeCoordinator:
    def __init__(
        self,
        *,
        qt_app: object,
        platform_services: PlatformServices,
        manifests: list[PluginManifest],
        plugin_context: PluginContext,
        background_manager: BackgroundManager,
        session_manager: PluginSessionManager,
        surface_coordinator: object,
        launcher_bridge: object,
        launcher_window: object | None,
        on_quit: Callable[[], None],
    ) -> None:
        self._qt_app = qt_app
        self._platform_services = platform_services
        self._manifests = manifests
        self._plugin_context = plugin_context
        self._background_manager = background_manager
        self._session_manager = session_manager
        self._surface_coordinator = surface_coordinator
        self._bridge = launcher_bridge
        self._launcher_window = launcher_window
        self._on_quit = on_quit
        self._log = get_logger("app.launcher_runtime")
        self._background_plugins_started = False
        self._launcher_prewarmed = False
        self._hotkeys_registered = False
        self._launcher_window_macos_configured = False
        self._last_hotkey_signal_at = 0.0
        self._last_show_request_at = 0.0
        self._last_clipboard_open_at = 0.0
        self._hotkey_coordinator = HotkeyCoordinator(
            platform_services,
            qt_app,
            on_launcher_toggle=self.toggle_launcher,
            on_clipboard_toggle=self.open_clipboard_history,
            on_plugin_launched=self.open_plugin,
        )

    @property
    def hotkey_coordinator(self) -> HotkeyCoordinator:
        return self._hotkey_coordinator

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

    def install_hotkeys(self) -> None:
        started_at = perf_counter()
        filters = self._hotkey_coordinator.root_filters()
        self._qt_app.setProperty("_hotkeyFilters", filters)
        self._log.debug(
            "hotkey.install_filters",
            "安装全局热键事件过滤器",
            filterCount=len(filters),
            elapsedMs=int((perf_counter() - started_at) * 1000),
        )
        QTimer.singleShot(500, self.register_hotkeys)
        self._log.debug("hotkey.register_scheduled", "全局热键注册已调度", delayMs=500)
        if not self._is_macos():
            QTimer.singleShot(1200, self.prewarm_launcher_window)
            self._log.debug("launcher.prewarm_scheduled", "启动器窗口预热已调度", delayMs=1200)

    def shutdown(self) -> None:
        self._hotkey_coordinator.unregister_all()

    def start_background_plugins(self) -> None:
        if self._background_plugins_started:
            return
        self._background_plugins_started = True
        self._background_manager.start_all()
        self._connect_clipboard_config_changed()
        if self._hotkeys_registered:
            self.refresh_clipboard_hotkey()

    def register_hotkeys(self) -> None:
        started_at = perf_counter()
        hwnd = 0
        if self._launcher_window and self._launcher_window.winId():
            hwnd = int(self._launcher_window.winId())
            self._configure_launcher_window_for_macos()
        self._log.debug(
            "hotkey.register_begin",
            "开始注册全局热键",
            launcherWindowFound=self._launcher_window is not None,
            launcherHwnd=hwnd,
        )
        if hwnd:
            self._hotkey_coordinator.assign_hwnd(hwnd)
        self._hotkey_coordinator.register_all(
            self._manifests,
            clipboard_hotkey=self._clipboard_hotkey_text(),
        )
        self._hotkeys_registered = True
        property_started_at = perf_counter()
        self._qt_app.setProperty("_pluginHotkeyFilters", self._hotkey_coordinator.plugin_filters())
        self._log.debug(
            "hotkey.register_end",
            "全局热键注册流程完成",
            pluginFilterCount=len(self._hotkey_coordinator.plugin_filters()),
            propertyElapsedMs=int((perf_counter() - property_started_at) * 1000),
            elapsedMs=int((perf_counter() - started_at) * 1000),
        )

    def refresh_clipboard_hotkey(self) -> None:
        self._log.debug("hotkey.clipboard_refresh", "刷新剪切板热键")
        self._hotkey_coordinator.refresh_clipboard_hotkey(self._clipboard_hotkey_text())

    def toggle_launcher(self) -> None:
        signal_at = perf_counter()
        self._last_hotkey_signal_at = signal_at
        if self._launcher_window is None or not is_qobject_alive(self._launcher_window):
            self._log.warning("launcher.toggle_failed", "启动器窗口不存在或已销毁")
            return
        state_started_at = perf_counter()
        before_visible = bool(self._launcher_window.isVisible())
        before_active = bool(getattr(self._launcher_window, "isActive", lambda: False)())
        self._log.debug(
            "launcher.toggle_begin",
            "准备切换启动器窗口",
            visible=before_visible,
            active=before_active,
            width=int(self._launcher_window.width()) if hasattr(self._launcher_window, "width") else 0,
            height=int(self._launcher_window.height()) if hasattr(self._launcher_window, "height") else 0,
            stateElapsedMs=int((perf_counter() - state_started_at) * 1000),
        )
        if self._launcher_window.isVisible():
            hide_started_at = perf_counter()
            self._launcher_window.hide()
            self._log.debug("launcher.hidden_by_hotkey", "启动器已由热键隐藏", elapsedMs=int((perf_counter() - hide_started_at) * 1000))
            return
        self._restore_launcher_window_state()
        show_result = self._show_launcher_window(activate=True)
        check_app_index = getattr(self._bridge, "checkAppIndex", None)
        if callable(check_app_index):
            check_app_index()
        self._last_show_request_at = perf_counter()
        elapsed_ms = show_result["elapsedMs"]
        log_show = self._log.warning if elapsed_ms >= 120 else self._log.debug
        log_show(
            "launcher.show_requested",
            "已请求显示并激活启动器窗口",
            visible=bool(self._launcher_window.isVisible()),
            active=bool(getattr(self._launcher_window, "isActive", lambda: False)()),
            x=int(self._launcher_window.x()) if hasattr(self._launcher_window, "x") else 0,
            y=int(self._launcher_window.y()) if hasattr(self._launcher_window, "y") else 0,
            centerElapsedMs=show_result["centerElapsedMs"],
            showCallElapsedMs=show_result["showCallElapsedMs"],
            raiseElapsedMs=show_result["raiseElapsedMs"],
            activateElapsedMs=show_result["activateElapsedMs"],
            fromSignalMs=int((perf_counter() - signal_at) * 1000),
            elapsedMs=elapsed_ms,
        )
        QTimer.singleShot(50, lambda started_at=signal_at: self._activate_and_log_launcher_window("launcher.state_after_show_50ms", started_at))

    def prewarm_launcher_window(self) -> None:
        if self._launcher_prewarmed:
            return
        self._launcher_prewarmed = True
        if self._launcher_window is None or not is_qobject_alive(self._launcher_window):
            self._log.warning("launcher.prewarm_skipped", "启动器窗口预热跳过，窗口不存在")
            return
        if self._launcher_window.isVisible():
            self._log.debug("launcher.prewarm_skipped", "启动器窗口预热跳过，窗口已显示")
            return
        started_at = perf_counter()
        old_opacity = 1.0
        show_result = {
            "centerElapsedMs": 0,
            "showCallElapsedMs": 0,
            "raiseElapsedMs": 0,
            "activateElapsedMs": 0,
            "elapsedMs": 0,
        }
        hide_elapsed_ms = 0
        try:
            old_opacity = float(self._launcher_window.opacity())
        except (AttributeError, RuntimeError, TypeError, ValueError):
            old_opacity = 1.0
        try:
            self._launcher_window.setOpacity(0.0)
            self._launcher_window.setProperty("prewarming", True)
            show_result = self._show_launcher_window(activate=False)
            hide_started_at = perf_counter()
            self._launcher_window.hide()
            hide_elapsed_ms = int((perf_counter() - hide_started_at) * 1000)
        except Exception as exc:
            self._log.warning("launcher.prewarm_failed", "启动器窗口预热失败", error=str(exc))
        finally:
            self._restore_launcher_window_state(opacity=old_opacity, hide=True)
        self._log.debug(
            "launcher.prewarm_complete",
            "启动器窗口预热完成",
            centerElapsedMs=show_result["centerElapsedMs"],
            showCallElapsedMs=show_result["showCallElapsedMs"],
            raiseElapsedMs=show_result["raiseElapsedMs"],
            activateElapsedMs=show_result["activateElapsedMs"],
            hideElapsedMs=hide_elapsed_ms,
            elapsedMs=int((perf_counter() - started_at) * 1000),
        )

    def hide_launcher(self) -> None:
        if self._launcher_window is not None and is_qobject_alive(self._launcher_window):
            self._launcher_window.hide()

    def open_clipboard_history(self) -> None:
        now = perf_counter()
        if now - self._last_clipboard_open_at < 0.35:
            self._log.debug(
                "hotkey.clipboard_debounced",
                "剪切板热键重复触发已忽略",
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

        shown = self._surface_coordinator.show(
            request.plugin_id,
            session,
            input_text=request.input_text,
            payload=request.payload,
        )
        if not shown:
            self._session_manager.unload_plugin(request.plugin_id)
            return
        if session.launch_mode == "none":
            self._session_manager.unload_plugin(request.plugin_id)

    def suspend_plugin(self, plugin_id: str, host: str) -> None:
        if not plugin_id:
            return
        normalized_host = "window" if host == "window" else "list" if host == "list" else "inline"
        self._surface_coordinator.suspend(plugin_id, normalized_host)
        self._session_manager.suspend_plugin(plugin_id, normalized_host)

    def on_surface_retained_close(self, plugin_id: str, host: str) -> None:
        self._session_manager.suspend_plugin(plugin_id, "window" if host == "window" else "inline")

    def on_retention_expired(self, plugin_id: str, state: SessionState) -> None:
        self._surface_coordinator.notify_retention_expired(plugin_id, state)
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
        if self._launcher_window is not None and is_qobject_alive(self._launcher_window):
            self._launcher_window.detachInlinePlugin(plugin_id)
        shown = self._surface_coordinator.show(
            plugin_id,
            session,
            payload=request.payload,
        )
        if not shown:
            self._session_manager.unload_plugin(plugin_id)

    def force_close_plugin(self, plugin_id: str) -> None:
        if plugin_id:
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
        if self._launcher_window is not None and is_qobject_alive(self._launcher_window):
            plugin_id = str(self._launcher_window.property("mixedPluginId") or "")
            plugin_mode = str(self._launcher_window.property("mixedPluginMode") or "")
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
            and self._launcher_window is not None
            and is_qobject_alive(self._launcher_window)
        ):
            self._launcher_window.setSearchInputSilently("")

    def _center_launcher_window(self) -> None:
        if self._launcher_window is None or not is_qobject_alive(self._launcher_window):
            return
        screen = None
        focus_point = focused_window_point()
        if focus_point is not None:
            try:
                screen = self._qt_app.screenAt(focus_point)
            except (RuntimeError, TypeError):
                screen = None
        if screen is None:
            screen = self._qt_app.screenAt(QCursor.pos())
        if screen is None:
            try:
                screen = self._launcher_window.screen()
            except RuntimeError:
                screen = None
        if screen is None:
            screen = self._qt_app.primaryScreen()
        _set_window_screen(self._launcher_window, screen)
        _center_window_once(
            self._launcher_window,
            screen,
            int(self._launcher_window.width()) or 800,
            int(self._launcher_window.height()) or 600,
        )

    def _restore_launcher_window_state(self, *, opacity: float = 1.0, hide: bool = False) -> None:
        if self._launcher_window is None or not is_qobject_alive(self._launcher_window):
            return
        try:
            self._launcher_window.setProperty("prewarming", False)
        except RuntimeError:
            return
        try:
            self._launcher_window.setOpacity(opacity)
        except (AttributeError, RuntimeError):
            pass
        if hide:
            try:
                self._launcher_window.hide()
            except RuntimeError:
                pass

    def _show_launcher_window(self, *, activate: bool) -> dict[str, int]:
        if self._launcher_window is None or not is_qobject_alive(self._launcher_window):
            return {
                "centerElapsedMs": 0,
                "showCallElapsedMs": 0,
                "raiseElapsedMs": 0,
                "activateElapsedMs": 0,
                "elapsedMs": 0,
            }
        started_at = perf_counter()
        center_started_at = perf_counter()
        self._configure_launcher_window_for_macos()
        self._center_launcher_window()
        center_elapsed_ms = int((perf_counter() - center_started_at) * 1000)
        show_call_started_at = perf_counter()
        self._launcher_window.show()
        self._configure_launcher_window_for_macos(force=True)
        show_call_elapsed_ms = int((perf_counter() - show_call_started_at) * 1000)
        raise_started_at = perf_counter()
        if activate:
            raise_window = getattr(self._launcher_window, "raise_", None)
            if callable(raise_window):
                raise_window()
        raise_elapsed_ms = int((perf_counter() - raise_started_at) * 1000)
        activate_started_at = perf_counter()
        if activate:
            self._activate_launcher_window_native()
            self._launcher_window.requestActivate()
        activate_elapsed_ms = int((perf_counter() - activate_started_at) * 1000)
        return {
            "centerElapsedMs": center_elapsed_ms,
            "showCallElapsedMs": show_call_elapsed_ms,
            "raiseElapsedMs": raise_elapsed_ms,
            "activateElapsedMs": activate_elapsed_ms,
            "elapsedMs": int((perf_counter() - started_at) * 1000),
        }

    def _log_launcher_window_state(self, event: str = "launcher.state_after_show", signal_at: float | None = None) -> None:
        if self._launcher_window is None or not is_qobject_alive(self._launcher_window):
            self._log.warning("launcher.state_after_show_missing", "显示请求后启动器窗口不存在或已销毁")
            return
        now = perf_counter()
        self._log.debug(
            event,
            "显示请求后的启动器窗口状态",
            visible=bool(self._launcher_window.isVisible()),
            active=bool(getattr(self._launcher_window, "isActive", lambda: False)()),
            x=int(self._launcher_window.x()) if hasattr(self._launcher_window, "x") else 0,
            y=int(self._launcher_window.y()) if hasattr(self._launcher_window, "y") else 0,
            width=int(self._launcher_window.width()) if hasattr(self._launcher_window, "width") else 0,
            height=int(self._launcher_window.height()) if hasattr(self._launcher_window, "height") else 0,
            fromSignalMs=int((now - (signal_at or self._last_hotkey_signal_at)) * 1000) if (signal_at or self._last_hotkey_signal_at) else 0,
            fromShowRequestMs=int((now - self._last_show_request_at) * 1000) if self._last_show_request_at else 0,
        )

    def _activate_and_log_launcher_window(self, event: str, signal_at: float) -> None:
        if self._launcher_window is not None and is_qobject_alive(self._launcher_window):
            self._configure_launcher_window_for_macos(force=True)
            raise_window = getattr(self._launcher_window, "raise_", None)
            if callable(raise_window):
                raise_window()
            self._activate_launcher_window_native()
            self._launcher_window.requestActivate()
        self._log_launcher_window_state(event, signal_at)

    def _configure_launcher_window_for_macos(self, *, force: bool = False) -> None:
        if self._launcher_window_macos_configured and not force:
            return
        if not self._is_macos():
            return
        if self._launcher_window is None or not is_qobject_alive(self._launcher_window):
            return
        try:
            from app.platform.macos.windowing import configure_launcher_window

            self._launcher_window_macos_configured = configure_launcher_window(self._launcher_window)
        except Exception as exc:
            self._log.debug("launcher.macos_window_config_failed", "macOS 启动器窗口配置失败", error=str(exc))

    def _activate_launcher_window_native(self) -> None:
        if not self._is_macos():
            return
        try:
            from app.platform.macos.windowing import activate_window

            activate_window(self._launcher_window)
        except Exception as exc:
            self._log.debug("launcher.macos_activate_failed", "macOS 启动器窗口原生激活失败", error=str(exc))

    def _is_macos(self) -> bool:
        return getattr(self._platform_services.info, "name", "") == "macos"

    def _clipboard_hotkey_text(self) -> str:
        service = self._plugin_context.services.clipboard
        store = getattr(service, "store", None)
        if store is None:
            return ""
        return str(store.get_config_value("hotkey") or "")

    def _connect_clipboard_config_changed(self) -> None:
        clipboard_service = self._plugin_context.services.clipboard
        add_listener = getattr(clipboard_service, "add_config_listener", None)
        if callable(add_listener):
            add_listener(self.refresh_clipboard_hotkey)
            return
        clipboard_store = getattr(clipboard_service, "store", None)
        config_changed = getattr(clipboard_store, "configChanged", None)
        connect = getattr(config_changed, "connect", None)
        if callable(connect):
            connect(self.refresh_clipboard_hotkey)

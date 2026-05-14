"""Application entry point for the uTools-like launcher runtime."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import shiboken6
from PySide6.QtCore import QFileSystemWatcher, QObject, QTimer, QUrl
from PySide6.QtGui import QCursor, QIcon
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from .app_relauncher import restart_current_app
from .app_view_model import AppViewModel
from .commands.command_index_db import CommandIndexDb
from .commands.command_service import CommandService
from .commands.dynamic_command_registry import DynamicCommandRegistry
from .launcher.launcher_bridge import LauncherBridge
from .platform.dynamic_commands import PlatformCommandApiFactory
from .platform.factory import create_platform_services
from .platform.storage import PlatformStorageFactory
from .plugins.background_manager import BackgroundManager
from .plugins.manifest_loader import load_all_plugin_manifests
from .plugins.plugin_manager import PluginManager
from .plugins.runtime import PluginContext, PluginSession
from .plugins.session_manager import PluginSessionManager, SessionState
from .qta_icon_provider import QtAwesomeImageProvider
from .storage import StorageManager
from .tray.system_tray_manager import SystemTrayManager


@dataclass(slots=True)
class PluginWindowSurface:
    """Track the live QML window that hosts a plugin session."""

    plugin_id: str
    window: QObject
    hidden_for_retention: bool = False


def _icon_from_manifest(value: str, app_dir: Path) -> QIcon:
    if not value:
        return QIcon()
    if value.startswith("qta:"):
        try:
            import qtawesome as qta

            return qta.icon(value.removeprefix("qta:"), color="#8B5CF6")
        except Exception:
            return QIcon()
    if value.startswith("file:///"):
        return QIcon(QUrl(value).toLocalFile())
    if value.startswith("qrc:/") or value.startswith(":/"):
        return QIcon(value)
    icon_path = app_dir / "assets" / "icons" / f"{value}.svg"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon(value)


def _plugin_window_config(session: PluginSession, screen: object = None) -> dict:
    options = session.manifest.window_options or {}
    if options.get("fullscreen"):
        return {"fullscreen": True, "width": 800, "height": 600}
    if screen is not None:
        screen_geo = screen.availableGeometry()
        sw, sh = screen_geo.width(), screen_geo.height()
    else:
        sw, sh = 1920, 1080
    return {
        "fullscreen": False,
        "width": _resolve_dimension(options.get("width"), sw, 800),
        "height": _resolve_dimension(options.get("height"), sh, 600),
    }


def _resolve_dimension(value: object, screen_size: int, default: int) -> int:
    if value is None:
        return default
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    if num < 1.0:
        return max(400, int(screen_size * num))
    return max(400, int(num))


def _is_qobject_alive(obj: object) -> bool:
    if obj is None:
        return False
    try:
        return shiboken6.isValid(obj)
    except RuntimeError:
        return False


def _set_window_size_if_alive(win: object, width: int, height: int) -> None:
    if not _is_qobject_alive(win):
        return
    try:
        win.setWidth(width)
        win.setHeight(height)
    except RuntimeError as exc:
        if "already deleted" in str(exc) or "Internal C++ object" in str(exc):
            return
        raise


def _center_window_once(win: QObject, screen: object, width: int, height: int) -> None:
    if screen is None or not _is_qobject_alive(win):
        return
    geometry = screen.availableGeometry()
    x = geometry.x() + max(0, (geometry.width() - width) // 2)
    y = geometry.y() + max(0, (geometry.height() - height) // 2)
    win.setX(x)
    win.setY(y)


class QmlHotReloader(QObject):
    def __init__(
        self,
        engine: QQmlApplicationEngine,
        qml_files: list[Path],
        watch_root: Path,
    ) -> None:
        super().__init__()
        self._engine = engine
        self._qml_files = qml_files
        self._watch_root = watch_root
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)
        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.setInterval(180)
        self._reload_timer.timeout.connect(self._reload)
        self._refresh_watch_files()

    def _all_qml_files(self) -> list[str]:
        return [str(path) for path in self._watch_root.rglob("*.qml") if path.is_file()]

    def _refresh_watch_files(self) -> None:
        current = set(self._watcher.files())
        desired = set(self._all_qml_files())
        to_remove = list(current - desired)
        to_add = [path for path in (desired - current) if Path(path).exists()]
        if to_remove:
            self._watcher.removePaths(to_remove)
        if to_add:
            self._watcher.addPaths(to_add)

    def _on_file_changed(self, _path: str) -> None:
        self._refresh_watch_files()
        self._reload_timer.start()

    def _reload(self) -> None:
        old_roots = list(self._engine.rootObjects())
        self._engine.clearComponentCache()
        for qml_file in self._qml_files:
            self._engine.load(QUrl.fromLocalFile(str(qml_file)))
        new_roots = self._engine.rootObjects()
        if len(new_roots) > len(old_roots):
            for root in old_roots:
                root.deleteLater()
        self._refresh_watch_files()


def _assign_hwnd_if_supported(manager: object, hwnd: int) -> None:
    set_hwnd = getattr(manager, "set_hwnd", None)
    if callable(set_hwnd):
        set_hwnd(hwnd)


def main() -> int:
    QQuickStyle.setStyle("Basic")
    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)

    engine = QQmlApplicationEngine()
    engine.addImageProvider("qta", QtAwesomeImageProvider())

    app_vm = AppViewModel()
    ctx = engine.rootContext()
    ctx.setContextProperty("app", app_vm)

    platform_services = create_platform_services(qt_app)
    storage = StorageManager()
    dynamic_commands = DynamicCommandRegistry()
    platform_services.storage_factory = PlatformStorageFactory(storage)
    platform_services.dynamic_command_api_factory = PlatformCommandApiFactory(dynamic_commands)
    platform_api = platform_services.create_api()
    command_index = CommandIndexDb(storage.database("command_index.db", wal=True, check_same_thread=False))
    manifests = load_all_plugin_manifests()
    plugin_manager = PluginManager(manifests)
    plugin_context = PluginContext(
        command_index=command_index,
        dynamic_commands=dynamic_commands,
        platform=platform_api,
        services={"platform": platform_api, "storage": storage},
    )
    background_mgr = BackgroundManager(manifests, plugin_manager, plugin_context)
    command_service = CommandService(
        manifests,
        command_index,
        dynamic_commands,
        platform_services=platform_services,
    )
    bridge = LauncherBridge(command_service, plugin_context.services)

    ctx.setContextProperty("launcherBridge", bridge)
    background_mgr.start_all()

    app_dir = Path(__file__).parent
    main_qml = app_dir / "Main.qml"
    plugin_window_qml = app_dir / "launcher" / "PluginWindow.qml"

    engine.load(QUrl.fromLocalFile(str(main_qml)))
    if not engine.rootObjects():
        return 1

    launcher_window = None
    for root_obj in engine.rootObjects():
        if root_obj.objectName() == "launcherWindow":
            launcher_window = root_obj

    hotkey_mgr = platform_services.hotkey_factory.create(
        parent=qt_app,
        hotkey=platform_services.default_launcher_hotkey,
        hotkey_id=1,
    )
    clipboard_hotkey_mgr = platform_services.hotkey_factory.create(
        parent=qt_app,
        hotkey=platform_services.default_clipboard_hotkey,
        hotkey_id=2,
    )
    plugin_hotkey_managers: list[object] = []
    plugin_hotkey_filters: list[object] = []
    _plugin_windows: dict[str, PluginWindowSurface] = {}
    shutting_down = False

    def _plugin_host_from_state(state: SessionState) -> str:
        if state.endswith("window"):
            return "window"
        if state.endswith("list"):
            return "list"
        return "inline"

    def _remove_dead_window_surface(plugin_id: str) -> None:
        surface = _plugin_windows.get(plugin_id)
        if surface is None:
            return
        if not _is_qobject_alive(surface.window):
            _plugin_windows.pop(plugin_id, None)

    def _get_live_window_surface(plugin_id: str) -> PluginWindowSurface | None:
        _remove_dead_window_surface(plugin_id)
        return _plugin_windows.get(plugin_id)

    def _notify_inline_host_retained(plugin_id: str) -> None:
        if launcher_window is not None and _is_qobject_alive(launcher_window):
            launcher_window.retainInlineHost(plugin_id)

    def _notify_inline_host_destroy(plugin_id: str) -> None:
        bridge.retainedPluginExpired.emit(plugin_id)

    def _show_retained_window(plugin_id: str) -> bool:
        surface = _get_live_window_surface(plugin_id)
        if surface is None:
            return False
        surface.hidden_for_retention = False
        win = surface.window
        try:
            win.show()
            win.raise_()
            win.requestActivate()
            return True
        except RuntimeError:
            _plugin_windows.pop(plugin_id, None)
            return False

    def _force_destroy_window(plugin_id: str) -> None:
        surface = _plugin_windows.pop(plugin_id, None)
        if surface is None:
            return
        win = surface.window
        if not _is_qobject_alive(win):
            return
        try:
            win.setProperty("retainOnClose", False)
            win.close()
        except RuntimeError:
            return

    def _show_window_surface(plugin_id: str, session: PluginSession) -> bool:
        surface = _get_live_window_surface(plugin_id)
        if surface is not None:
            try:
                surface.hidden_for_retention = False
                surface.window.show()
                surface.window.raise_()
                surface.window.requestActivate()
                return True
            except RuntimeError:
                _plugin_windows.pop(plugin_id, None)
        return _open_independent_window(plugin_id, session)

    def _on_plugin_retention_expired(plugin_id: str, state: SessionState) -> None:
        """Destroy the retained UI surface first, then unload the Python session.

        The ordering matters. QML items may still hold bindings into the
        ViewModel, so we ask the UI to disappear before disposing the session.
        """

        host = _plugin_host_from_state(state)
        if host == "window":
            _force_destroy_window(plugin_id)
        else:
            _notify_inline_host_destroy(plugin_id)
        session_mgr.unload_plugin(plugin_id)

    session_mgr = PluginSessionManager(
        ctx,
        plugin_manager,
        plugin_context,
        on_retention_expired=_on_plugin_retention_expired,
    )

    def _clipboard_hotkey_text() -> str:
        service = plugin_context.services.get("clipboard.background")
        store = getattr(service, "store", None)
        if store is None:
            return ""
        return str(store.get_config_value("hotkey") or "")

    def _try_register_hotkey() -> None:
        hwnd = 0
        if launcher_window and launcher_window.winId():
            hwnd = int(launcher_window.winId())
        if hwnd:
            _assign_hwnd_if_supported(hotkey_mgr, hwnd)
            _assign_hwnd_if_supported(clipboard_hotkey_mgr, hwnd)
            for manager in plugin_hotkey_managers:
                _assign_hwnd_if_supported(manager, hwnd)
        if not hotkey_mgr.register():
            print(
                f"[WARN] global hotkey register failed: {platform_services.default_launcher_hotkey}"
            )
        _try_register_clipboard_hotkey()
        _try_register_plugin_hotkeys()

    def _try_register_clipboard_hotkey() -> None:
        hotkey = _clipboard_hotkey_text()
        clipboard_hotkey_mgr.unregister()
        if not hotkey:
            return
        if not clipboard_hotkey_mgr.register(hotkey):
            print(f"[WARN] clipboard hotkey register failed: {hotkey}")

    def _plugin_hotkey_specs() -> list[tuple[str, str, str, dict]]:
        specs: list[tuple[str, str, str, dict]] = []
        for manifest in manifests:
            for command in manifest.commands or [manifest.primary_command]:
                hotkey = command.hotkey.strip()
                if not hotkey:
                    continue
                specs.append((manifest.id, command.id, hotkey, command.payload))
        return specs

    def _prepare_for_recreate(plugin_id: str, payload: dict) -> None:
        """Tear down retained UI when a new action cannot safely reuse the session."""

        state = session_mgr.get_session_state(plugin_id)
        if state is None:
            return
        host = _plugin_host_from_state(state)
        if host == "window":
            _force_destroy_window(plugin_id)
        else:
            _notify_inline_host_destroy(plugin_id)
        if payload.get("clearLauncherInputOnEnter") and launcher_window and _is_qobject_alive(launcher_window):
            launcher_window.setSearchInputSilently("")

    def _try_register_plugin_hotkeys() -> None:
        for manager in plugin_hotkey_managers:
            manager.unregister()
        plugin_hotkey_managers.clear()
        plugin_hotkey_filters.clear()

        if launcher_window is None:
            return
        hwnd = int(launcher_window.winId()) if launcher_window.winId() else 0
        for index, (plugin_id, command_id, hotkey, payload) in enumerate(
            _plugin_hotkey_specs(),
            start=10,
        ):
            manager = platform_services.hotkey_factory.create(
                parent=qt_app,
                hotkey=hotkey,
                hotkey_id=index,
            )
            if hwnd:
                _assign_hwnd_if_supported(manager, hwnd)
            manager.hotkeyPressed.connect(
                lambda pid=plugin_id, cid=command_id, data=payload: on_plugin_launched(
                    pid,
                    cid,
                    "",
                    data,
                )
            )
            if manager.register():
                plugin_hotkey_managers.append(manager)
                hotkey_filter_item = platform_services.hotkey_factory.install_filter(
                    qt_app,
                    manager,
                )
                if hotkey_filter_item is not None:
                    plugin_hotkey_filters.append(hotkey_filter_item)
            else:
                print(f"[WARN] plugin hotkey register failed: {hotkey} ({plugin_id})")
        qt_app.setProperty("_pluginHotkeyFilters", plugin_hotkey_filters)

    QTimer.singleShot(500, _try_register_hotkey)

    root_hotkey_filters: list[object] = []
    hotkey_filter = platform_services.hotkey_factory.install_filter(qt_app, hotkey_mgr)
    if hotkey_filter is not None:
        root_hotkey_filters.append(hotkey_filter)
    clipboard_hotkey_filter = platform_services.hotkey_factory.install_filter(
        qt_app,
        clipboard_hotkey_mgr,
    )
    if clipboard_hotkey_filter is not None:
        root_hotkey_filters.append(clipboard_hotkey_filter)
    qt_app.setProperty("_hotkeyFilters", root_hotkey_filters)

    def toggle_launcher() -> None:
        if launcher_window is None or not _is_qobject_alive(launcher_window):
            return
        if launcher_window.isVisible():
            launcher_window.hide()
        else:
            _center_launcher_window()
            launcher_window.show()
            launcher_window.requestActivate()

    hotkey_mgr.hotkeyPressed.connect(toggle_launcher)

    def _center_launcher_window() -> None:
        if launcher_window is None or not _is_qobject_alive(launcher_window):
            return
        screen = qt_app.screenAt(QCursor.pos())
        if screen is None:
            try:
                screen = launcher_window.screen()
            except RuntimeError:
                screen = None
        if screen is None:
            screen = qt_app.primaryScreen()
        _center_window_once(
            launcher_window,
            screen,
            int(launcher_window.width()) or 800,
            int(launcher_window.height()) or 600,
        )

    def _open_independent_window(plugin_id: str, session: PluginSession) -> bool:
        manifest = session.manifest
        target_screen = None
        if launcher_window is not None:
            try:
                target_screen = launcher_window.screen()
            except RuntimeError:
                target_screen = None
        if target_screen is None:
            target_screen = qt_app.screenAt(QCursor.pos()) or qt_app.primaryScreen()

        wc = _plugin_window_config(session, target_screen)
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(plugin_window_qml)))
        win = component.createWithInitialProperties(
            {
                "pluginId": plugin_id,
                "pluginName": manifest.name,
                "qmlPage": session.qml_page(),
                "initialWidth": wc["width"],
                "initialHeight": wc["height"],
                "retainOnClose": True,
            }
        )
        if win is None:
            print(f"[ERROR] failed to create plugin window: {plugin_id} - {component.errorString()}")
            session_mgr.unload_plugin(plugin_id)
            return False

        win.setProperty("pluginId", plugin_id)
        win.setProperty("pluginName", manifest.name)
        win.setProperty("qmlPage", session.qml_page())
        win.setProperty("initialWidth", wc["width"])
        win.setProperty("initialHeight", wc["height"])
        win.setProperty("retainOnClose", True)
        if wc["fullscreen"]:
            win.showFullScreen()
        else:
            win.setWidth(wc["width"])
            win.setHeight(wc["height"])
        if hasattr(win, "setIcon"):
            win.setIcon(_icon_from_manifest(manifest.icon, app_dir))

        if not wc["fullscreen"]:
            _center_window_once(win, target_screen, wc["width"], wc["height"])

        def _on_retained_close_requested(pid: str) -> None:
            surface = _plugin_windows.get(pid)
            if surface is not None:
                surface.hidden_for_retention = True
            session_mgr.suspend_plugin(pid, "window")

        win.retainedCloseRequested.connect(_on_retained_close_requested)
        win.destroyed.connect(lambda _obj=None, pid=plugin_id: _plugin_windows.pop(pid, None))

        _plugin_windows[plugin_id] = PluginWindowSurface(plugin_id=plugin_id, window=win)

        if launcher_window:
            launcher_window.hide()

        win.show()
        if not wc["fullscreen"]:
            QTimer.singleShot(
                0,
                lambda w=win, width=wc["width"], height=wc["height"]: _set_window_size_if_alive(
                    w,
                    width,
                    height,
                ),
            )
        win.requestActivate()
        return True

    def _show_inline_plugin(plugin_id: str, session: PluginSession, input_text: str, payload: dict) -> None:
        if launcher_window is None or not _is_qobject_alive(launcher_window):
            return
        launcher_window.enterPluginMode(
            plugin_id,
            "inline_view",
            input_text,
            bool(payload.get("clearLauncherInputOnEnter")),
            session.qml_page(),
        )

    def _show_list_plugin(plugin_id: str, input_text: str, payload: dict) -> None:
        if launcher_window is None or not _is_qobject_alive(launcher_window):
            return
        launcher_window.enterPluginMode(
            plugin_id,
            "list",
            input_text,
            bool(payload.get("clearLauncherInputOnEnter")),
            "",
        )

    def on_plugin_launched(plugin_id: str, command_id: str, input_text: str, payload: dict) -> None:
        preferred_host = "window" if payload.get("openInWindow") else None
        if session_mgr.has_session(plugin_id) and not session_mgr.can_reuse_plugin(
            plugin_id,
            command_id=command_id,
            input_text=input_text,
            payload=payload,
        ):
            _prepare_for_recreate(plugin_id, payload)

        session = session_mgr.open_plugin(
            plugin_id,
            command_id=command_id,
            input_text=input_text,
            payload=payload,
            preferred_host=preferred_host,
        )
        if session is None:
            return

        launch_mode = "window" if payload.get("openInWindow") else session.launch_mode
        if launch_mode == "none":
            session_mgr.unload_plugin(plugin_id)
            if launcher_window:
                launcher_window.hide()
            return
        if launch_mode == "list":
            bridge.setPluginListItems(session.list_model())
            _show_list_plugin(plugin_id, input_text, payload)
            return
        if launch_mode == "inline_view":
            _show_inline_plugin(plugin_id, session, input_text, payload)
            return
        _show_window_surface(plugin_id, session)

    def open_clipboard_history() -> None:
        on_plugin_launched("clipboard", "", "", {})

    clipboard_hotkey_mgr.hotkeyPressed.connect(open_clipboard_history)

    clipboard_service = plugin_context.services.get("clipboard.background")
    clipboard_store = getattr(clipboard_service, "store", None)
    if clipboard_store is not None:
        clipboard_store.configChanged.connect(_try_register_clipboard_hotkey)

    def on_plugin_input_edited(plugin_id: str, text: str) -> None:
        items = session_mgr.update_plugin_input(plugin_id, text)
        if session_mgr.plugin_launch_mode(plugin_id) == "list":
            bridge.setPluginListItems(items)

    def on_plugin_list_item_activated(plugin_id: str, item_id: str) -> None:
        items = session_mgr.activate_list_item(plugin_id, item_id)
        bridge.setPluginListItems(items)

    def on_plugin_list_item_action(plugin_id: str, item_id: str, action_id: str) -> None:
        items = session_mgr.activate_list_item_action(plugin_id, item_id, action_id)
        bridge.setPluginListItems(items)

    def on_plugin_suspended(plugin_id: str, host: str) -> None:
        if host == "window":
            session_mgr.suspend_plugin(plugin_id, "window")
            return
        if host == "list":
            bridge.setPluginListItems([])
            session_mgr.suspend_plugin(plugin_id, "list")
            return
        bridge.setPluginListItems([])
        _notify_inline_host_retained(plugin_id)
        session_mgr.suspend_plugin(plugin_id, "inline")

    def on_plugin_detached_to_window(plugin_id: str) -> None:
        session = session_mgr.open_plugin(
            plugin_id,
            preferred_host="window",
            payload={"openInWindow": True},
        )
        if session is None:
            return
        if launcher_window is not None and _is_qobject_alive(launcher_window):
            launcher_window.detachInlinePlugin(plugin_id)
        _show_window_surface(plugin_id, session)

    bridge.pluginCommandLaunched.connect(on_plugin_launched)
    bridge.pluginClosed.connect(session_mgr.unload_plugin)
    bridge.pluginSuspended.connect(on_plugin_suspended)
    bridge.pluginDetachedToWindow.connect(on_plugin_detached_to_window)
    bridge.pluginInputEdited.connect(on_plugin_input_edited)
    bridge.pluginListItemActivated.connect(on_plugin_list_item_activated)
    bridge.pluginListItemActionActivated.connect(on_plugin_list_item_action)

    def restart_app() -> None:
        restart_current_app()
        qt_app.quit()

    bridge.restartRequested.connect(restart_app)
    bridge.hideLauncherRequested.connect(
        lambda: launcher_window.hide()
        if launcher_window and _is_qobject_alive(launcher_window)
        else None
    )

    def shutdown_runtime() -> None:
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        hotkey_mgr.unregister()
        clipboard_hotkey_mgr.unregister()
        for manager in plugin_hotkey_managers:
            manager.unregister()
        for surface in list(_plugin_windows.values()):
            if _is_qobject_alive(surface.window):
                try:
                    surface.window.setProperty("retainOnClose", False)
                    surface.window.close()
                except RuntimeError:
                    pass
        session_mgr.close_all()
        background_mgr.stop_all()
        plugin_manager.close_all()
        command_index.close()

    qt_app.aboutToQuit.connect(shutdown_runtime)

    tray_mgr = SystemTrayManager(parent=qt_app)
    tray_mgr.showWindowRequested.connect(toggle_launcher)
    tray_mgr.restartRequested.connect(restart_app)
    tray_mgr.quitRequested.connect(qt_app.quit)
    tray_mgr.show()

    if os.getenv("PY_DESKTOP_QML_HOT_RELOAD", "").strip() in {"1", "true", "TRUE"}:
        hot_reloader = QmlHotReloader(
            engine,
            [main_qml, plugin_window_qml],
            Path(__file__).parents[1],
        )
        qt_app.setProperty("_qmlHotReloader", hot_reloader)

    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

"""Manages QML plugin windows and inline/list host surfaces."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import shiboken6
from PySide6.QtCore import QPoint, QObject, QTimer, QUrl
from PySide6.QtGui import QIcon, QCursor
from PySide6.QtQml import QQmlComponent, QQmlApplicationEngine

from app.logging import get_logger
from app.plugins.runtime import PluginSession
from app.plugins.session_manager import SessionState


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
    always_on_top = bool(options.get("alwaysOnTop") or options.get("always_on_top"))
    if options.get("fullscreen"):
        return {"fullscreen": True, "width": 800, "height": 600, "alwaysOnTop": always_on_top}
    if screen is not None:
        screen_geo = screen.availableGeometry()
        sw, sh = screen_geo.width(), screen_geo.height()
    else:
        sw, sh = 1920, 1080
    return {
        "fullscreen": False,
        "width": _resolve_dimension(options.get("width"), sw, 800),
        "height": _resolve_dimension(options.get("height"), sh, 600),
        "alwaysOnTop": always_on_top,
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
    except (RuntimeError, TypeError):
        return False


def is_qobject_alive(obj: object) -> bool:
    return _is_qobject_alive(obj)


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


def _window_dimension(win: object, name: str, default: int) -> int:
    value = getattr(win, name, None)
    try:
        raw = value() if callable(value) else value
        size = int(raw)
    except (TypeError, ValueError, RuntimeError):
        return default
    return size if size > 0 else default


def focused_window_point() -> QPoint | None:
    if sys.platform != "darwin":
        return None
    try:
        from app.platform.macos.windowing import focused_window_center

        point = focused_window_center()
    except Exception:
        return None
    if point is None:
        return None
    try:
        x, y = point
        return QPoint(round(float(x)), round(float(y)))
    except (TypeError, ValueError):
        return None


def _configure_macos_overlay_window(window: object, *, force_top: bool = True) -> bool:
    if sys.platform != "darwin":
        return False
    try:
        from app.platform.macos.windowing import configure_overlay_window

        return configure_overlay_window(window, force_top=force_top)
    except Exception:
        return False


def _activate_macos_window(window: object) -> bool:
    if sys.platform != "darwin":
        return False
    try:
        from app.platform.macos.windowing import activate_window

        return activate_window(window)
    except Exception:
        return False


def _center_window_once(win: object, screen: object, width: int, height: int) -> None:
    if screen is None or not _is_qobject_alive(win):
        return
    geometry = screen.availableGeometry()
    x = geometry.x() + max(0, (geometry.width() - width) // 2)
    y = geometry.y() + max(0, (geometry.height() - height) // 2)
    win.setX(x)
    win.setY(y)


def _set_window_screen(win: object, screen: object) -> None:
    if screen is None or not _is_qobject_alive(win):
        return
    set_screen = getattr(win, "setScreen", None)
    if callable(set_screen):
        try:
            set_screen(screen)
        except RuntimeError:
            return


class PluginSurfaceCoordinator:
    """Creates and manages QML surfaces for plugin sessions.

    Handles independent windows, inline host integration, list mode,
    window retention/hide on close, and full destruction when sessions expire.
    """

    def __init__(
        self,
        engine: QQmlApplicationEngine,
        qt_app: object,
        *,
        plugin_window_qml_path: str,
        app_dir: Path,
        launcher_bridge: object | None = None,
        launcher_window: object | None = None,
        on_retained_close: Callable[[str, str], None] | None = None,
    ) -> None:
        self._engine = engine
        self._qt_app = qt_app
        self._plugin_window_qml_path = plugin_window_qml_path
        self._app_dir = app_dir
        self._bridge = launcher_bridge
        self._launcher_window = launcher_window
        self._on_retained_close = on_retained_close
        self._windows: dict[str, PluginWindowSurface] = {}
        self._opening_windows: set[str] = set()
        self._log = get_logger("app.plugin_surface_coordinator")

    def show(
        self,
        plugin_id: str,
        session: PluginSession,
        *,
        input_text: str = "",
        payload: dict | None = None,
    ) -> bool:
        launch_mode = session.launch_mode
        if payload and payload.get("openInWindow"):
            launch_mode = "window"

        if launch_mode == "none":
            if self._launcher_window is not None and _is_qobject_alive(self._launcher_window):
                self._launcher_window.hide()
            return True
        if launch_mode == "list":
            if self._bridge is not None:
                self._bridge.setPluginListItems(session.list_model())
            self._show_list_plugin(plugin_id, input_text, payload or {})
            return True
        if launch_mode == "inline_view":
            self._show_inline_plugin(plugin_id, session, input_text, payload or {})
            return True
        return self._show_window_surface(plugin_id, session)

    def suspend(self, plugin_id: str, host: str) -> None:
        if host == "window":
            return
        if host == "list":
            if self._bridge is not None:
                self._bridge.setPluginListItems([])
            return
        if self._bridge is not None:
            self._bridge.setPluginListItems([])
        self._notify_inline_host_retained(plugin_id)

    def destroy(self, plugin_id: str) -> None:
        surface = self._windows.pop(plugin_id, None)
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

    def destroy_all(self) -> None:
        for surface in list(self._windows.values()):
            if _is_qobject_alive(surface.window):
                try:
                    surface.window.setProperty("retainOnClose", False)
                    surface.window.close()
                except RuntimeError:
                    pass

    def notify_retention_expired(self, plugin_id: str, state: SessionState) -> None:
        host = self._host_from_state(state)
        if host == "window":
            self.destroy(plugin_id)
        else:
            if self._bridge is not None:
                self._bridge.retainedPluginExpired.emit(plugin_id)

    def _show_window_surface(self, plugin_id: str, session: PluginSession) -> bool:
        surface = self._get_live_surface(plugin_id)
        if surface is not None:
            try:
                surface.hidden_for_retention = False
                self._move_window_to_target_screen(surface.window)
                surface.window.show()
                self._configure_surface_window(
                    surface.window,
                    force_top=bool(surface.window.property("alwaysOnTop")),
                )
                surface.window.raise_()
                _activate_macos_window(surface.window)
                surface.window.requestActivate()
                QTimer.singleShot(50, lambda w=surface.window: self._activate_surface_window(w))
                return True
            except RuntimeError:
                self._windows.pop(plugin_id, None)
        if plugin_id in self._opening_windows:
            return True
        self._opening_windows.add(plugin_id)
        try:
            return self._open_independent_window(plugin_id, session)
        finally:
            self._opening_windows.discard(plugin_id)

    def _open_independent_window(self, plugin_id: str, session: PluginSession) -> bool:
        manifest = session.manifest
        target_screen = self._target_screen()
        wc = _plugin_window_config(session, target_screen)
        component = QQmlComponent(self._engine, QUrl.fromLocalFile(self._plugin_window_qml_path))
        win = component.createWithInitialProperties(
            {
                "pluginId": plugin_id,
                "pluginName": manifest.name,
                "qmlPage": session.qml_page(),
                "initialWidth": wc["width"],
                "initialHeight": wc["height"],
                "alwaysOnTop": wc["alwaysOnTop"],
                "retainOnClose": True,
            }
        )
        if win is None:
            self._log.error("plugin.window.create_failed", "创建插件窗口失败", pluginId=plugin_id, error=component.errorString())
            return False

        win.setProperty("pluginId", plugin_id)
        win.setProperty("pluginName", manifest.name)
        win.setProperty("qmlPage", session.qml_page())
        win.setProperty("initialWidth", wc["width"])
        win.setProperty("initialHeight", wc["height"])
        win.setProperty("alwaysOnTop", wc["alwaysOnTop"])
        win.setProperty("retainOnClose", True)
        if wc["fullscreen"]:
            win.showFullScreen()
        else:
            win.setWidth(wc["width"])
            win.setHeight(wc["height"])
        if hasattr(win, "setIcon"):
            win.setIcon(_icon_from_manifest(manifest.icon, self._app_dir))

        self._configure_surface_window(win, force_top=wc["alwaysOnTop"])
        _set_window_screen(win, target_screen)

        if not wc["fullscreen"]:
            _center_window_once(win, target_screen, wc["width"], wc["height"])

        def _on_retained_close(pid: str) -> None:
            surface = self._windows.get(pid)
            if surface is not None:
                surface.hidden_for_retention = True
            if self._on_retained_close is not None:
                self._on_retained_close(pid, "window")

        win.retainedCloseRequested.connect(_on_retained_close)
        win.destroyed.connect(lambda _obj=None, pid=plugin_id, window=win: self._forget_window_surface(pid, window))

        self._windows[plugin_id] = PluginWindowSurface(plugin_id=plugin_id, window=win)

        if self._launcher_window is not None:
            self._launcher_window.hide()

        win.show()
        self._configure_surface_window(win, force_top=wc["alwaysOnTop"])
        raise_window = getattr(win, "raise_", None)
        if callable(raise_window):
            raise_window()
        if not wc["fullscreen"]:
            QTimer.singleShot(
                0,
                lambda w=win, width=wc["width"], height=wc["height"]: _set_window_size_if_alive(
                    w, width, height
                ),
            )
        _activate_macos_window(win)
        win.requestActivate()
        QTimer.singleShot(50, lambda w=win: self._activate_surface_window(w))
        return True

    def _show_inline_plugin(self, plugin_id: str, session: PluginSession, input_text: str, payload: dict) -> None:
        if self._launcher_window is None or not _is_qobject_alive(self._launcher_window):
            return
        self._launcher_window.enterPluginMode(
            plugin_id,
            "inline_view",
            input_text,
            bool(payload.get("clearLauncherInputOnEnter")),
            session.qml_page(),
        )

    def _show_list_plugin(self, plugin_id: str, input_text: str, payload: dict) -> None:
        if self._launcher_window is None or not _is_qobject_alive(self._launcher_window):
            return
        self._launcher_window.enterPluginMode(
            plugin_id,
            "list",
            input_text,
            bool(payload.get("clearLauncherInputOnEnter")),
            "",
        )

    def _get_live_surface(self, plugin_id: str) -> PluginWindowSurface | None:
        surface = self._windows.get(plugin_id)
        if surface is None:
            return self._adopt_existing_window_surface(plugin_id)
        if not _is_qobject_alive(surface.window):
            self._windows.pop(plugin_id, None)
            return self._adopt_existing_window_surface(plugin_id)
        self._close_duplicate_window_surfaces(plugin_id, surface.window)
        return surface

    def _forget_window_surface(self, plugin_id: str, window: object) -> None:
        surface = self._windows.get(plugin_id)
        if surface is not None and surface.window is window:
            self._windows.pop(plugin_id, None)

    def _adopt_existing_window_surface(self, plugin_id: str) -> PluginWindowSurface | None:
        windows_fn = getattr(self._qt_app, "topLevelWindows", None)
        if not callable(windows_fn):
            return None
        matches = [
            window
            for window in windows_fn()
            if _is_qobject_alive(window) and str(window.property("pluginId") or "") == plugin_id
        ]
        if not matches:
            return None
        primary = next((window for window in matches if bool(getattr(window, "isVisible", lambda: False)())), matches[0])
        surface = PluginWindowSurface(plugin_id=plugin_id, window=primary)
        self._windows[plugin_id] = surface
        self._close_duplicate_window_surfaces(plugin_id, primary)
        return surface

    def _close_duplicate_window_surfaces(self, plugin_id: str, keep_window: object) -> None:
        windows_fn = getattr(self._qt_app, "topLevelWindows", None)
        if not callable(windows_fn):
            return
        for window in list(windows_fn()):
            if window is keep_window or not _is_qobject_alive(window):
                continue
            if str(window.property("pluginId") or "") != plugin_id:
                continue
            try:
                window.setProperty("retainOnClose", False)
                window.close()
            except RuntimeError:
                pass

    def _move_window_to_target_screen(self, window: object) -> None:
        target_screen = self._target_screen(fallback_window=window)
        if target_screen is None:
            return
        current_screen = None
        screen_fn = getattr(window, "screen", None)
        if callable(screen_fn):
            try:
                current_screen = screen_fn()
            except RuntimeError:
                current_screen = None
        _set_window_screen(window, target_screen)
        if current_screen is target_screen:
            return
        width = _window_dimension(window, "width", 800)
        height = _window_dimension(window, "height", 600)
        _center_window_once(window, target_screen, width, height)

    def _configure_surface_window(self, window: object, *, force_top: bool = True) -> None:
        _configure_macos_overlay_window(window, force_top=force_top)

    def _activate_surface_window(self, window: object) -> None:
        if not _is_qobject_alive(window):
            return
        try:
            force_top = bool(window.property("alwaysOnTop"))
        except RuntimeError:
            return
        self._configure_surface_window(window, force_top=force_top)
        raise_window = getattr(window, "raise_", None)
        if callable(raise_window):
            try:
                raise_window()
            except RuntimeError:
                return
        _activate_macos_window(window)
        request_activate = getattr(window, "requestActivate", None)
        if callable(request_activate):
            try:
                request_activate()
            except RuntimeError:
                return

    def _target_screen(self, *, fallback_window: object | None = None) -> object | None:
        screen_at = getattr(self._qt_app, "screenAt", None)
        if callable(screen_at):
            focus_point = focused_window_point()
            if focus_point is not None:
                try:
                    screen = screen_at(focus_point)
                except (RuntimeError, TypeError):
                    screen = None
                if screen is not None:
                    return screen
            try:
                screen = screen_at(QCursor.pos())
            except (RuntimeError, TypeError):
                screen = None
            if screen is not None:
                return screen
        if fallback_window is not None:
            screen_fn = getattr(fallback_window, "screen", None)
            if callable(screen_fn):
                try:
                    screen = screen_fn()
                except RuntimeError:
                    screen = None
                if screen is not None:
                    return screen
        if self._launcher_window is not None:
            screen_fn = getattr(self._launcher_window, "screen", None)
            if callable(screen_fn):
                try:
                    screen = screen_fn()
                except RuntimeError:
                    screen = None
                if screen is not None:
                    return screen
        primary_screen = getattr(self._qt_app, "primaryScreen", None)
        if callable(primary_screen):
            return primary_screen()
        return None

    def _notify_inline_host_retained(self, plugin_id: str) -> None:
        if self._launcher_window is not None and _is_qobject_alive(self._launcher_window):
            self._launcher_window.retainInlineHost(plugin_id)

    @staticmethod
    def _host_from_state(state: SessionState) -> str:
        return state.host

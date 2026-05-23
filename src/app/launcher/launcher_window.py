from __future__ import annotations

import os
from time import perf_counter

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCursor

from app.logging import get_logger
from app.platform.services import PlatformServices
from app.plugins.host import focused_window_point, is_qobject_alive


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


class LauncherWindowController:
    def __init__(
        self,
        *,
        qt_app: object,
        platform_services: PlatformServices,
        launcher_window: object | None,
    ) -> None:
        self._qt_app = qt_app
        self._platform_services = platform_services
        self._launcher_window = launcher_window
        self._log = get_logger("app.launcher.window")
        self._macos_configured = False
        self._prewarmed = False
        self._last_show_request_at = 0.0

    def is_available(self) -> bool:
        return self._launcher_window is not None and is_qobject_alive(self._launcher_window)

    def is_visible(self) -> bool:
        return self.is_available() and bool(self._launcher_window.isVisible())

    def window_id(self) -> int:
        if not self.is_available():
            return 0
        try:
            return int(self._launcher_window.winId())
        except (RuntimeError, TypeError, ValueError):
            return 0

    def snapshot(self) -> dict[str, object]:
        if not self.is_available():
            return {
                "visible": False,
                "active": False,
                "x": 0,
                "y": 0,
                "width": 0,
                "height": 0,
            }
        return {
            "visible": bool(self._launcher_window.isVisible()),
            "active": bool(getattr(self._launcher_window, "isActive", lambda: False)()),
            "x": int(self._launcher_window.x()) if hasattr(self._launcher_window, "x") else 0,
            "y": int(self._launcher_window.y()) if hasattr(self._launcher_window, "y") else 0,
            "width": int(self._launcher_window.width()) if hasattr(self._launcher_window, "width") else 0,
            "height": int(self._launcher_window.height()) if hasattr(self._launcher_window, "height") else 0,
        }

    def hide(self) -> None:
        if self.is_available():
            self._launcher_window.hide()

    def restore_state(self, *, opacity: float = 1.0, hide: bool = False) -> None:
        if not self.is_available():
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

    def show(self, *, activate: bool) -> dict[str, int]:
        if not self.is_available():
            return {
                "centerElapsedMs": 0,
                "showCallElapsedMs": 0,
                "raiseElapsedMs": 0,
                "activateElapsedMs": 0,
                "elapsedMs": 0,
            }
        started_at = perf_counter()
        center_started_at = perf_counter()
        self.configure_for_macos()
        self.center()
        center_elapsed_ms = int((perf_counter() - center_started_at) * 1000)
        show_call_started_at = perf_counter()
        self._launcher_window.show()
        self.configure_for_macos(force=True)
        show_call_elapsed_ms = int((perf_counter() - show_call_started_at) * 1000)
        raise_started_at = perf_counter()
        if activate:
            raise_window = getattr(self._launcher_window, "raise_", None)
            if callable(raise_window):
                raise_window()
        raise_elapsed_ms = int((perf_counter() - raise_started_at) * 1000)
        activate_started_at = perf_counter()
        if activate:
            self.activate_native()
            self._launcher_window.requestActivate()
        activate_elapsed_ms = int((perf_counter() - activate_started_at) * 1000)
        self._last_show_request_at = perf_counter()
        return {
            "centerElapsedMs": center_elapsed_ms,
            "showCallElapsedMs": show_call_elapsed_ms,
            "raiseElapsedMs": raise_elapsed_ms,
            "activateElapsedMs": activate_elapsed_ms,
            "elapsedMs": int((perf_counter() - started_at) * 1000),
        }

    def prewarm(self) -> None:
        if self._prewarmed:
            return
        self._prewarmed = True
        if not self.is_available():
            self._log.warning("launcher.prewarm_skipped", "启动器窗口预热跳过，窗口不存在")
            return
        if self.is_visible():
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
            show_result = self.show(activate=False)
            hide_started_at = perf_counter()
            self._launcher_window.hide()
            hide_elapsed_ms = int((perf_counter() - hide_started_at) * 1000)
        except Exception as exc:
            self._log.warning("launcher.prewarm_failed", "启动器窗口预热失败", error=str(exc))
        finally:
            self.restore_state(opacity=old_opacity, hide=True)
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

    def center(self) -> None:
        if not self.is_available():
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

    def activate_and_log(self, event: str, signal_at: float) -> None:
        if self.is_available():
            self.configure_for_macos(force=True)
            raise_window = getattr(self._launcher_window, "raise_", None)
            if callable(raise_window):
                raise_window()
            self.activate_native()
            self._launcher_window.requestActivate()
        self.log_state(event, signal_at)

    def log_state(self, event: str = "launcher.state_after_show", signal_at: float | None = None) -> None:
        if not self.is_available():
            self._log.warning("launcher.state_after_show_missing", "显示请求后启动器窗口不存在或已销毁")
            return
        now = perf_counter()
        state = self.snapshot()
        self._log.debug(
            event,
            "显示请求后的启动器窗口状态",
            visible=state["visible"],
            active=state["active"],
            x=state["x"],
            y=state["y"],
            width=state["width"],
            height=state["height"],
            fromSignalMs=int((now - signal_at) * 1000) if signal_at else 0,
            fromShowRequestMs=int((now - self._last_show_request_at) * 1000) if self._last_show_request_at else 0,
        )

    def configure_for_macos(self, *, force: bool = False) -> None:
        if self._macos_configured and not force:
            return
        if not self._is_macos():
            return
        if not self.is_available():
            return
        try:
            from app.platform.macos.windowing import configure_launcher_window

            self._macos_configured = configure_launcher_window(self._launcher_window)
        except Exception as exc:
            self._log.debug("launcher.macos_window_config_failed", "macOS 启动器窗口配置失败", error=str(exc))

    def activate_native(self) -> None:
        if self._is_macos():
            try:
                from app.platform.macos.windowing import activate_window

                activate_window(self._launcher_window)
            except Exception as exc:
                self._log.debug("launcher.macos_activate_failed", "macOS 启动器窗口原生激活失败", error=str(exc))
            return
        if self._is_windows():
            try:
                from app.platform.windows.windowing import activate_window

                activate_window(self._launcher_window, force_top=True)
            except Exception as exc:
                self._log.debug("launcher.windows_activate_failed", "Windows 启动器窗口原生激活失败", error=str(exc))

    def detach_inline_plugin(self, plugin_id: str) -> None:
        if self.is_available():
            self._launcher_window.detachInlinePlugin(plugin_id)

    def set_search_input_silently(self, text: str) -> None:
        if self.is_available():
            self._launcher_window.setSearchInputSilently(text)

    def current_mixed_plugin(self) -> tuple[str, str]:
        if not self.is_available():
            return "", ""
        return (
            str(self._launcher_window.property("mixedPluginId") or ""),
            str(self._launcher_window.property("mixedPluginMode") or ""),
        )

    def _is_macos(self) -> bool:
        return getattr(self._platform_services.info, "name", "") == "macos"

    def _is_windows(self) -> bool:
        return getattr(self._platform_services.info, "name", "") == "windows"

    @staticmethod
    def prewarm_enabled() -> bool:
        return os.getenv("PY_DESKTOP_PREWARM_LAUNCHER", "").strip().lower() in {"1", "true", "yes", "on"}

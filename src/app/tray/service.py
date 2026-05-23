from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject

from .system_tray_manager import SystemTrayManager


class TrayService:
    def __init__(
        self,
        *,
        parent: QObject,
        on_show_window: Callable[[], None],
        on_restart: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._manager = SystemTrayManager(parent=parent)
        self._manager.showWindowRequested.connect(on_show_window)
        self._manager.restartRequested.connect(on_restart)
        self._manager.quitRequested.connect(on_quit)

    def show(self) -> None:
        self._manager.show()

    def hide(self) -> None:
        self._manager.hide()

    def show_message(self, title: str, message: str) -> None:
        self._manager.show_message(title, message)

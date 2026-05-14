from __future__ import annotations

from PySide6.QtCore import QObject

from app.hotkey.win_hotkey_manager import WinHotkeyFilter, WinHotkeyManager


class WindowsHotkeyFactory:
    def create(self, *, parent: object | None, hotkey: str, hotkey_id: int) -> WinHotkeyManager:
        owner = parent if isinstance(parent, QObject) else None
        return WinHotkeyManager(parent=owner, hotkey=hotkey, hotkey_id=hotkey_id)

    def install_filter(self, app: object, manager: WinHotkeyManager) -> WinHotkeyFilter | None:
        if app is None or manager is None:
            return None
        hotkey_filter = WinHotkeyFilter(manager)
        install_filter = getattr(app, "installNativeEventFilter", None)
        if callable(install_filter):
            install_filter(hotkey_filter)
        return hotkey_filter

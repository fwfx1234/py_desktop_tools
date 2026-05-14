from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class NoopHotkeyManager(QObject):
    hotkeyPressed = Signal()

    def __init__(self, parent: QObject | None = None, *, hotkey: str = "", hotkey_id: int = 0) -> None:
        super().__init__(parent)
        self._hotkey = hotkey
        self._hotkey_id = hotkey_id

    def register(self, hotkey: str | None = None) -> bool:
        if hotkey is not None:
            self._hotkey = hotkey
        return False

    def unregister(self) -> None:
        return

    def is_registered(self) -> bool:
        return False


class NoopHotkeyFactory:
    def create(self, *, parent: object | None, hotkey: str, hotkey_id: int) -> NoopHotkeyManager:
        owner = parent if isinstance(parent, QObject) else None
        return NoopHotkeyManager(owner, hotkey=hotkey, hotkey_id=hotkey_id)

    def install_filter(self, app: object, manager: object) -> object | None:
        del app, manager
        return None

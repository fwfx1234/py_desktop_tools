from __future__ import annotations

from typing import Protocol


class HotkeyManagerProtocol(Protocol):
    hotkeyPressed: object

    def register(self, hotkey: str | None = None) -> bool:
        ...

    def unregister(self) -> None:
        ...

    def is_registered(self) -> bool:
        ...


class HotkeyFactoryProtocol(Protocol):
    def create(self, *, parent: object | None, hotkey: str, hotkey_id: int) -> HotkeyManagerProtocol:
        ...

    def install_filter(self, app: object, manager: HotkeyManagerProtocol) -> object | None:
        ...

"""Windows global hotkey manager based on RegisterHotKey."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QObject, Signal, QAbstractNativeEventFilter

# Win32 constants
MOD_WIN = 0x0008
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
WM_HOTKEY = 0x0312

HOTKEY_ID = 1

user32 = ctypes.windll.user32
user32.RegisterHotKey.restype = wintypes.BOOL
user32.RegisterHotKey.argtypes = [wintypes.HWND, wintypes.INT, wintypes.UINT, wintypes.UINT]
user32.UnregisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, wintypes.INT]


class WinHotkeyFilter(QAbstractNativeEventFilter):
    """Capture WM_HOTKEY and forward one configured id to its manager."""

    def __init__(self, manager: WinHotkeyManager) -> None:
        super().__init__()
        self._manager = manager

    def nativeEventFilter(self, eventType, message) -> tuple[bool, int]:
        del eventType
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == WM_HOTKEY and msg.wParam == self._manager.hotkey_id:
            self._manager.hotkeyPressed.emit()
            return True, 0
        return False, 0


class WinHotkeyManager(QObject):
    """Register one global hotkey and emit hotkeyPressed when it fires."""

    hotkeyPressed = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        hotkey: str = "Alt+Space",
        hotkey_id: int = HOTKEY_ID,
    ) -> None:
        super().__init__(parent)
        self._registered = False
        self._hwnd = 0
        self._hotkey = hotkey
        self._hotkey_id = hotkey_id

    @property
    def hotkey_id(self) -> int:
        return self._hotkey_id

    def register(self, hotkey: str | None = None) -> bool:
        """Register the configured hotkey. Returns whether it succeeded."""
        if hotkey is not None:
            self._hotkey = hotkey
        parsed = parse_hotkey(self._hotkey)
        if parsed is None:
            self._registered = False
            return False
        if self._registered:
            self.unregister()
        modifiers, virtual_key = parsed
        result = user32.RegisterHotKey(
            self._hwnd,
            self._hotkey_id,
            modifiers,
            virtual_key,
        )
        if result:
            self._registered = True
        else:
            self._registered = False
        return bool(result)

    def set_hwnd(self, hwnd: int) -> None:
        """Set the HWND used by RegisterHotKey."""
        self._hwnd = hwnd

    def unregister(self) -> None:
        """Unregister the current hotkey."""
        if self._registered:
            user32.UnregisterHotKey(self._hwnd, self._hotkey_id)
            self._registered = False

    def is_registered(self) -> bool:
        return self._registered


def parse_hotkey(hotkey: str) -> tuple[int, int] | None:
    """Parse strings such as Alt+V, Ctrl+Alt+V, or Alt+Space."""
    parts = [part.strip() for part in hotkey.replace("＋", "+").split("+") if part.strip()]
    if not parts:
        return None

    modifiers = 0
    key_part = ""
    for part in parts:
        token = part.lower()
        if token in {"ctrl", "control"}:
            modifiers |= MOD_CONTROL
        elif token == "alt":
            modifiers |= MOD_ALT
        elif token == "shift":
            modifiers |= MOD_SHIFT
        elif token in {"win", "meta", "cmd"}:
            modifiers |= MOD_WIN
        else:
            key_part = part

    if not key_part:
        return None
    virtual_key = _virtual_key(key_part)
    if virtual_key is None:
        return None
    return modifiers, virtual_key


def _virtual_key(key: str) -> int | None:
    token = key.strip().lower()
    aliases = {
        "space": 0x20,
        "enter": 0x0D,
        "return": 0x0D,
        "esc": 0x1B,
        "escape": 0x1B,
        "tab": 0x09,
        "backspace": 0x08,
        "delete": 0x2E,
        "del": 0x2E,
        "insert": 0x2D,
        "home": 0x24,
        "end": 0x23,
        "pageup": 0x21,
        "pagedown": 0x22,
        "left": 0x25,
        "up": 0x26,
        "right": 0x27,
        "down": 0x28,
    }
    if token in aliases:
        return aliases[token]
    if len(token) == 1 and token.isalnum():
        return ord(token.upper())
    if token.startswith("f") and token[1:].isdigit():
        index = int(token[1:])
        if 1 <= index <= 24:
            return 0x70 + index - 1
    return None

from __future__ import annotations

import ctypes
import os
import time
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal, Slot

from app.logging import get_logger

from .keyboard_hook import LOW_LEVEL_HOTKEY_HOOK


MOD_WIN = 0x0008
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
WM_HOTKEY = 0x0312
HOTKEY_ID = 1

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.RegisterHotKey.restype = wintypes.BOOL
user32.RegisterHotKey.argtypes = [wintypes.HWND, wintypes.INT, wintypes.UINT, wintypes.UINT]
user32.UnregisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, wintypes.INT]


def _log():
    return get_logger("app.platform.windows.hotkey")


class WinHotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, manager: WinHotkeyManager) -> None:
        super().__init__()
        self._manager = manager

    def nativeEventFilter(self, eventType, message) -> tuple[bool, int]:
        del eventType
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == WM_HOTKEY and msg.wParam == self._manager.hotkey_id:
            self._manager.emit_pressed("native")
            return True, 0
        return False, 0


class WinHotkeyManager(QObject):
    hotkeyPressed = Signal()
    _pressedQueued = Signal(str)

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
        self._registered_hwnd = 0
        self._native_registered = False
        self._fallback_registered = False
        self._hotkey = hotkey
        self._hotkey_id = hotkey_id
        self._last_error = 0
        self._last_emit_at = 0.0
        self._pressedQueued.connect(self.emit_pressed)

    @property
    def hotkey_id(self) -> int:
        return self._hotkey_id

    @property
    def last_error(self) -> int:
        return self._last_error

    @property
    def hotkey(self) -> str:
        return self._hotkey

    @property
    def native_registered(self) -> bool:
        return self._native_registered

    @property
    def fallback_registered(self) -> bool:
        return self._fallback_registered

    @property
    def last_emit_at(self) -> float:
        return self._last_emit_at

    def register(self, hotkey: str | None = None) -> bool:
        started_at = time.perf_counter()
        if hotkey is not None:
            self._hotkey = hotkey
        self._last_error = 0
        parsed = parse_hotkey(self._hotkey)
        if parsed is None:
            _log().warning(
                "hotkey.parse_failed",
                "Windows 热键解析失败",
                hotkey=self._hotkey,
                hotkeyId=self._hotkey_id,
                elapsedMs=int((time.perf_counter() - started_at) * 1000),
            )
            self._registered = False
            return False
        if self._registered:
            unregister_started_at = time.perf_counter()
            self.unregister()
            unregister_elapsed_ms = int((time.perf_counter() - unregister_started_at) * 1000)
            if self._registered:
                _log().warning(
                    "hotkey.unregister_before_register_failed",
                    "重新注册前卸载旧热键失败",
                    hotkey=self._hotkey,
                    hotkeyId=self._hotkey_id,
                    elapsedMs=unregister_elapsed_ms,
                )
                return False
        else:
            unregister_elapsed_ms = 0
        modifiers, virtual_key = parsed
        hwnd = self._hwnd or 0
        ctypes.set_last_error(0)
        native_started_at = time.perf_counter()
        result = user32.RegisterHotKey(
            hwnd,
            self._hotkey_id,
            modifiers,
            virtual_key,
        )
        native_elapsed_ms = int((time.perf_counter() - native_started_at) * 1000)
        self._native_registered = bool(result)
        self._registered_hwnd = hwnd if self._native_registered else 0
        if not self._native_registered:
            self._last_error = ctypes.get_last_error()
        fallback_elapsed_ms = 0
        if self._should_enable_fallback():
            fallback_started_at = time.perf_counter()
            self._fallback_registered = LOW_LEVEL_HOTKEY_HOOK.add(
                id(self),
                parsed,
                lambda: self._pressedQueued.emit("low_level"),
            )
            fallback_elapsed_ms = int((time.perf_counter() - fallback_started_at) * 1000)
        else:
            self._fallback_registered = False
        self._registered = self._native_registered or self._fallback_registered
        log_register = _log().info if self._hotkey_id == HOTKEY_ID or self._fallback_registered or not self._registered else _log().debug
        log_register(
            "hotkey.register_result",
            "Windows 热键注册结果",
            hotkey=self._hotkey,
            hotkeyId=self._hotkey_id,
            nativeRegistered=self._native_registered,
            fallbackRegistered=self._fallback_registered,
            errorCode=self._last_error,
            modifiers=modifiers,
            virtualKey=virtual_key,
            unregisterElapsedMs=unregister_elapsed_ms,
            nativeElapsedMs=native_elapsed_ms,
            fallbackElapsedMs=fallback_elapsed_ms,
            elapsedMs=int((time.perf_counter() - started_at) * 1000),
        )
        return self._registered

    def set_hwnd(self, hwnd: int) -> None:
        self._hwnd = hwnd

    def unregister(self) -> None:
        if self._fallback_registered:
            LOW_LEVEL_HOTKEY_HOOK.remove(id(self))
            self._fallback_registered = False
        if self._native_registered:
            ctypes.set_last_error(0)
            result = user32.UnregisterHotKey(self._registered_hwnd, self._hotkey_id)
            if result:
                self._native_registered = False
                self._registered_hwnd = 0
                self._last_error = 0
            else:
                self._last_error = ctypes.get_last_error()
        self._registered = self._native_registered or self._fallback_registered

    def is_registered(self) -> bool:
        return self._registered

    @Slot(str)
    def emit_pressed(self, origin: str) -> None:
        now = time.perf_counter()
        if now - self._last_emit_at < 0.25:
            _log().debug(
                "hotkey.emit_debounced",
                "热键重复触发已防抖",
                hotkey=self._hotkey,
                hotkeyId=self._hotkey_id,
                origin=origin,
                sinceLastMs=int((now - self._last_emit_at) * 1000),
            )
            return
        self._last_emit_at = now
        _log().info(
            "hotkey.emit",
            "热键信号发出",
            hotkey=self._hotkey,
            hotkeyId=self._hotkey_id,
            origin=origin,
        )
        self.hotkeyPressed.emit()

    def _should_enable_fallback(self) -> bool:
        value = os.getenv("PY_DESKTOP_TOOLS_HOTKEY_HOOK", "").strip().lower()
        if value in {"1", "true", "yes", "on", "always"}:
            return True
        if value in {"0", "false", "no", "off", "never"}:
            return False
        if not self._native_registered:
            return True
        normalized = self._hotkey.strip().lower().replace("＋", "+")
        return self._hotkey_id in {1, 2} or normalized in {"alt+space", "alt+v"}


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


def parse_hotkey(hotkey: str) -> tuple[int, int] | None:
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


__all__ = [
    "HOTKEY_ID",
    "WinHotkeyFilter",
    "WinHotkeyManager",
    "WindowsHotkeyFactory",
    "parse_hotkey",
]

from __future__ import annotations

import ctypes
import ctypes.util
from time import perf_counter

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot


def _log():
    from app.logging import get_logger

    return get_logger("app.platform.macos.hotkey")


_NORMALIZED_ALT_NAMES = {"alt", "option"}
_NORMALIZED_CTRL_NAMES = {"ctrl", "control"}
_NORMALIZED_SHIFT_NAMES = {"shift"}
_NORMALIZED_CMD_NAMES = {"cmd", "command", "meta", "win"}
_CARBON_OPTION_KEY = 1 << 11
_CARBON_CONTROL_KEY = 1 << 12
_CARBON_SHIFT_KEY = 1 << 9
_CARBON_CMD_KEY = 1 << 8
_CARBON_NO_ERR = 0
_EVENT_NOT_HANDLED_ERR = -9874
_K_EVENT_CLASS_KEYBOARD = int.from_bytes(b"keyb", "big")
_K_EVENT_HOT_KEY_PRESSED = 5
_K_EVENT_PARAM_DIRECT_OBJECT = int.from_bytes(b"----", "big")
_TYPE_EVENT_HOT_KEY_ID = int.from_bytes(b"hkid", "big")
_HOTKEY_SIGNATURE = int.from_bytes(b"pdtl", "big")


class _CarbonEventTypeSpec(ctypes.Structure):
    _fields_ = [
        ("eventClass", ctypes.c_uint32),
        ("eventKind", ctypes.c_uint32),
    ]


class _CarbonEventHotKeyID(ctypes.Structure):
    _fields_ = [
        ("signature", ctypes.c_uint32),
        ("id", ctypes.c_uint32),
    ]


_EVENT_HANDLER = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
_CARBON = None
_CARBON_LOAD_FAILED = False


class MacHotkeyManager(QObject):
    hotkeyPressed = Signal()
    _pressedQueued = Signal(str)

    def __init__(self, parent: QObject | None = None, *, hotkey: str = "", hotkey_id: int = 0) -> None:
        super().__init__(parent)
        self._hotkey = hotkey
        self._hotkey_id = hotkey_id
        self._registered = False
        self._listener = None
        self._native_registered = False
        self._fallback_registered = False
        self._native_hotkey_ref = None
        self._native_handler_ref = None
        self._native_handler = None
        self._pressed_modifiers: set[str] = set()
        self._target_modifiers: set[str] = set()
        self._target_key = ""
        self._target_down = False
        self._last_emit_at = 0.0
        self._pressedQueued.connect(self.emit_pressed, Qt.ConnectionType.QueuedConnection)

    @property
    def hotkey_id(self) -> int:
        return self._hotkey_id

    @property
    def hotkey(self) -> str:
        return self._hotkey

    @property
    def last_emit_at(self) -> float:
        return self._last_emit_at

    @property
    def native_registered(self) -> bool:
        return self._native_registered

    @property
    def fallback_registered(self) -> bool:
        return self._fallback_registered

    def register(self, hotkey: str | None = None) -> bool:
        if hotkey is not None:
            self._hotkey = hotkey
        parsed = _parse_hotkey(self._hotkey)
        if parsed is None:
            self._registered = False
            return False
        self.unregister()
        self._target_modifiers, self._target_key = parsed
        if self._register_native(parsed):
            self._registered = True
            return True
        try:
            from pynput import keyboard
        except Exception as exc:
            _log().warning("hotkey.unavailable", "macOS 全局热键不可用", error=str(exc))
            return False

        def on_press(key):
            self._handle_press(key)

        def on_release(key):
            self._handle_release(key)

        try:
            self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self._listener.start()
            self._fallback_registered = True
            self._registered = True
            return True
        except Exception as exc:
            _log().warning("hotkey.register_failed", "macOS 全局热键注册失败", error=str(exc))
            self._listener = None
            self._fallback_registered = False
            self._registered = False
            return False

    def unregister(self) -> None:
        self._unregister_native()
        listener = self._listener
        self._listener = None
        if listener is not None:
            try:
                listener.stop()
            except Exception:
                pass
            join = getattr(listener, "join", None)
            if callable(join):
                try:
                    join(timeout=0.2)
                except RuntimeError:
                    pass
        self._fallback_registered = False
        self._pressed_modifiers.clear()
        self._target_down = False
        self._registered = self._native_registered or self._fallback_registered

    def is_registered(self) -> bool:
        return self._registered

    def _handle_press(self, key: object) -> None:
        normalized = _normalize_pressed_key(key)
        if not normalized:
            return
        if normalized in {"alt", "ctrl", "shift", "cmd"}:
            self._pressed_modifiers.add(normalized)
            return
        if normalized == self._target_key:
            if self._target_down:
                return
            self._target_down = True
            if self._pressed_modifiers == self._target_modifiers:
                self._queue_pressed("pynput")

    def _handle_release(self, key: object) -> None:
        normalized = _normalize_pressed_key(key)
        if normalized in {"alt", "ctrl", "shift", "cmd"}:
            self._pressed_modifiers.discard(normalized)
        elif normalized == self._target_key:
            self._target_down = False

    def _queue_pressed(self, origin: str) -> None:
        if QThread.currentThread() == self.thread():
            self.emit_pressed(origin)
        else:
            self._pressedQueued.emit(origin)

    @Slot(str)
    def emit_pressed(self, origin: str) -> None:
        now = perf_counter()
        if now - self._last_emit_at < 0.25:
            _log().debug(
                "hotkey.emit_debounced",
                "macOS 热键重复触发已防抖",
                hotkey=self._hotkey,
                hotkeyId=self._hotkey_id,
                origin=origin,
                sinceLastMs=int((now - self._last_emit_at) * 1000),
            )
            return
        self._last_emit_at = now
        _log().info(
            "hotkey.emit",
            "macOS 热键信号发出",
            hotkey=self._hotkey,
            hotkeyId=self._hotkey_id,
            origin=origin,
        )
        self.hotkeyPressed.emit()

    def _register_native(self, parsed: tuple[set[str], str]) -> bool:
        native = _native_hotkey(parsed)
        if native is None:
            return False
        carbon = _carbon()
        if carbon is None:
            return False
        key_code, modifiers = native
        target = carbon.GetEventDispatcherTarget()
        event_type = _CarbonEventTypeSpec(_K_EVENT_CLASS_KEYBOARD, _K_EVENT_HOT_KEY_PRESSED)
        handler_ref = ctypes.c_void_p()
        hotkey_id = _CarbonEventHotKeyID(_HOTKEY_SIGNATURE, self._hotkey_id)

        def handle_event(_next_handler, event, _user_data):
            received = _CarbonEventHotKeyID()
            status = carbon.GetEventParameter(
                event,
                _K_EVENT_PARAM_DIRECT_OBJECT,
                _TYPE_EVENT_HOT_KEY_ID,
                None,
                ctypes.sizeof(_CarbonEventHotKeyID),
                None,
                ctypes.byref(received),
            )
            if (
                status == _CARBON_NO_ERR
                and received.signature == _HOTKEY_SIGNATURE
                and received.id == self._hotkey_id
            ):
                self._queue_pressed("carbon")
                return _CARBON_NO_ERR
            return _EVENT_NOT_HANDLED_ERR

        handler = _EVENT_HANDLER(handle_event)
        status = carbon.InstallEventHandler(
            target,
            handler,
            1,
            ctypes.byref(event_type),
            None,
            ctypes.byref(handler_ref),
        )
        if status != _CARBON_NO_ERR:
            return False
        hotkey_ref = ctypes.c_void_p()
        status = carbon.RegisterEventHotKey(
            key_code,
            modifiers,
            hotkey_id,
            target,
            0,
            ctypes.byref(hotkey_ref),
        )
        if status != _CARBON_NO_ERR:
            carbon.RemoveEventHandler(handler_ref)
            _log().debug("hotkey.carbon_register_failed", "macOS Carbon 热键注册失败", hotkey=self._hotkey, hotkeyId=self._hotkey_id, status=status)
            return False
        self._native_handler = handler
        self._native_handler_ref = handler_ref
        self._native_hotkey_ref = hotkey_ref
        self._native_registered = True
        _log().debug("hotkey.carbon_registered", "macOS Carbon 热键注册成功", hotkey=self._hotkey, hotkeyId=self._hotkey_id)
        return True

    def _unregister_native(self) -> None:
        carbon = _carbon() if self._native_registered else None
        if carbon is not None:
            if self._native_hotkey_ref is not None:
                try:
                    carbon.UnregisterEventHotKey(self._native_hotkey_ref)
                except Exception:
                    pass
            if self._native_handler_ref is not None:
                try:
                    carbon.RemoveEventHandler(self._native_handler_ref)
                except Exception:
                    pass
        self._native_hotkey_ref = None
        self._native_handler_ref = None
        self._native_handler = None
        self._native_registered = False


class MacHotkeyFactory:
    def create(self, *, parent: object | None, hotkey: str, hotkey_id: int) -> MacHotkeyManager:
        owner = parent if isinstance(parent, QObject) else None
        return MacHotkeyManager(owner, hotkey=hotkey, hotkey_id=hotkey_id)

    def install_filter(self, app: object, manager: object) -> object | None:
        del app, manager
        return None


def _parse_hotkey(hotkey: str) -> tuple[set[str], str] | None:
    parts = [part.strip().lower() for part in hotkey.replace("＋", "+").split("+") if part.strip()]
    if not parts:
        return None
    modifiers: set[str] = set()
    key_name = ""
    for part in parts:
        if part in _NORMALIZED_ALT_NAMES:
            modifiers.add("alt")
        elif part in _NORMALIZED_CTRL_NAMES:
            modifiers.add("ctrl")
        elif part in _NORMALIZED_SHIFT_NAMES:
            modifiers.add("shift")
        elif part in _NORMALIZED_CMD_NAMES:
            modifiers.add("cmd")
        else:
            key_name = _normalize_key_name(part)
    if not key_name:
        return None
    return modifiers, key_name


def _native_hotkey(parsed: tuple[set[str], str]) -> tuple[int, int] | None:
    modifiers, key_name = parsed
    key_code = _MAC_KEY_CODES.get(key_name)
    if key_code is None:
        return None
    native_modifiers = 0
    for modifier in modifiers:
        if modifier == "alt":
            native_modifiers |= _CARBON_OPTION_KEY
        elif modifier == "ctrl":
            native_modifiers |= _CARBON_CONTROL_KEY
        elif modifier == "shift":
            native_modifiers |= _CARBON_SHIFT_KEY
        elif modifier == "cmd":
            native_modifiers |= _CARBON_CMD_KEY
    return key_code, native_modifiers


def _carbon():
    global _CARBON, _CARBON_LOAD_FAILED
    if _CARBON is not None:
        return _CARBON
    if _CARBON_LOAD_FAILED:
        return None
    path = ctypes.util.find_library("Carbon") or "/System/Library/Frameworks/Carbon.framework/Carbon"
    try:
        carbon = ctypes.CDLL(path)
        carbon.GetEventDispatcherTarget.restype = ctypes.c_void_p
        carbon.InstallEventHandler.argtypes = [
            ctypes.c_void_p,
            _EVENT_HANDLER,
            ctypes.c_uint32,
            ctypes.POINTER(_CarbonEventTypeSpec),
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        carbon.InstallEventHandler.restype = ctypes.c_int32
        carbon.RemoveEventHandler.argtypes = [ctypes.c_void_p]
        carbon.RemoveEventHandler.restype = ctypes.c_int32
        carbon.RegisterEventHotKey.argtypes = [
            ctypes.c_uint32,
            ctypes.c_uint32,
            _CarbonEventHotKeyID,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        carbon.RegisterEventHotKey.restype = ctypes.c_int32
        carbon.UnregisterEventHotKey.argtypes = [ctypes.c_void_p]
        carbon.UnregisterEventHotKey.restype = ctypes.c_int32
        carbon.GetEventParameter.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        carbon.GetEventParameter.restype = ctypes.c_int32
    except Exception as exc:
        _CARBON_LOAD_FAILED = True
        _log().debug("hotkey.carbon_unavailable", "macOS Carbon 热键不可用", error=str(exc))
        return None
    _CARBON = carbon
    return carbon


def _normalize_pressed_key(key: object) -> str:
    vk_name = _normalize_virtual_key(_extract_virtual_key(key))
    if vk_name:
        return vk_name
    char = getattr(key, "char", None)
    if isinstance(char, str) and char:
        return _normalize_key_name(char)
    name = getattr(key, "name", None)
    if isinstance(name, str) and name:
        return _normalize_key_name(name)
    return ""


def _extract_virtual_key(key: object) -> int | None:
    vk = getattr(key, "vk", None)
    if isinstance(vk, int):
        return vk
    value = getattr(key, "value", None)
    if isinstance(value, int):
        return value
    value_vk = getattr(value, "vk", None)
    if isinstance(value_vk, int):
        return value_vk
    return None


def _normalize_virtual_key(vk: int | None) -> str:
    if vk is None:
        return ""
    return _MAC_VIRTUAL_KEY_NAMES.get(vk, "")


def _normalize_key_name(name: str) -> str:
    token = name.strip().lower()
    aliases = {
        "return": "enter",
        "esc": "escape",
        "option": "alt",
        "option_l": "alt",
        "option_r": "alt",
        "alt_l": "alt",
        "alt_r": "alt",
        "control": "ctrl",
        "control_l": "ctrl",
        "control_r": "ctrl",
        "ctrl_l": "ctrl",
        "ctrl_r": "ctrl",
        "shift_l": "shift",
        "shift_r": "shift",
        "command": "cmd",
        "command_l": "cmd",
        "command_r": "cmd",
        "cmd_l": "cmd",
        "cmd_r": "cmd",
        "meta": "cmd",
        "win": "cmd",
    }
    return aliases.get(token, token)


_MAC_VIRTUAL_KEY_NAMES = {
    0x00: "a",
    0x01: "s",
    0x02: "d",
    0x03: "f",
    0x04: "h",
    0x05: "g",
    0x06: "z",
    0x07: "x",
    0x08: "c",
    0x09: "v",
    0x0B: "b",
    0x0C: "q",
    0x0D: "w",
    0x0E: "e",
    0x0F: "r",
    0x10: "y",
    0x11: "t",
    0x12: "1",
    0x13: "2",
    0x14: "3",
    0x15: "4",
    0x16: "6",
    0x17: "5",
    0x18: "=",
    0x19: "9",
    0x1A: "7",
    0x1B: "-",
    0x1C: "8",
    0x1D: "0",
    0x1E: "]",
    0x1F: "o",
    0x20: "u",
    0x21: "[",
    0x22: "i",
    0x23: "p",
    0x24: "enter",
    0x25: "l",
    0x26: "j",
    0x27: "'",
    0x28: "k",
    0x29: ";",
    0x2A: "\\",
    0x2B: ",",
    0x2C: "/",
    0x2D: "n",
    0x2E: "m",
    0x2F: ".",
    0x30: "tab",
    0x31: "space",
    0x33: "backspace",
    0x35: "escape",
    0x36: "cmd",
    0x37: "cmd",
    0x38: "shift",
    0x3A: "alt",
    0x3B: "ctrl",
    0x3C: "shift",
    0x3D: "alt",
    0x3E: "ctrl",
    0x7A: "f1",
    0x78: "f2",
    0x63: "f3",
    0x76: "f4",
    0x60: "f5",
    0x61: "f6",
    0x62: "f7",
    0x64: "f8",
    0x65: "f9",
    0x6D: "f10",
    0x67: "f11",
    0x6F: "f12",
    0x69: "f13",
    0x6B: "f14",
    0x71: "f15",
    0x6A: "f16",
    0x40: "f17",
    0x4F: "f18",
    0x50: "f19",
    0x73: "home",
    0x74: "pageup",
    0x75: "delete",
    0x77: "end",
    0x79: "pagedown",
    0x7B: "left",
    0x7C: "right",
    0x7D: "down",
    0x7E: "up",
}


_MAC_KEY_CODES = {
    name: code
    for code, name in _MAC_VIRTUAL_KEY_NAMES.items()
    if name not in {"alt", "ctrl", "shift", "cmd"}
}


__all__ = ["MacHotkeyFactory", "MacHotkeyManager"]

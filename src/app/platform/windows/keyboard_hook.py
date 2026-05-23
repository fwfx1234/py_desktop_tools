from __future__ import annotations

import ctypes
import threading
from collections.abc import Callable
from ctypes import wintypes
from time import perf_counter

from app.logging import get_logger


MOD_WIN = 0x0008
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
WH_KEYBOARD_LL = 13
HC_ACTION = 0
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_LWIN = 0x5B
VK_RWIN = 0x5C
LLKHF_ALTDOWN = 0x20

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32.GetAsyncKeyState.restype = wintypes.SHORT
user32.GetAsyncKeyState.argtypes = [wintypes.INT]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]

ULONG_PTR = wintypes.WPARAM
LRESULT = wintypes.LPARAM


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


LowLevelKeyboardProc = ctypes.WINFUNCTYPE(LRESULT, wintypes.INT, wintypes.WPARAM, wintypes.LPARAM)
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.SetWindowsHookExW.argtypes = [wintypes.INT, LowLevelKeyboardProc, wintypes.HINSTANCE, wintypes.DWORD]
user32.CallNextHookEx.restype = LRESULT
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, wintypes.INT, wintypes.WPARAM, wintypes.LPARAM]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.GetMessageW.restype = wintypes.BOOL
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.TranslateMessage.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = wintypes.LPARAM
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]


def _log():
    return get_logger("app.platform.windows.keyboard_hook")


class LowLevelHotkeyHook:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: dict[int, tuple[tuple[int, int], Callable[[], None]]] = {}
        self._active: set[int] = set()
        self._pressed_modifiers = 0
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._available = False
        self._hook = None
        self._proc = LowLevelKeyboardProc(self._callback)
        self._last_miss_log: dict[int, float] = {}

    def add(self, key: int, parsed: tuple[int, int], callback: Callable[[], None]) -> bool:
        self._ensure_started()
        if not self._available:
            return False
        with self._lock:
            self._items[key] = (parsed, callback)
            item_count = len(self._items)
        _log().info(
            "hotkey.low_level_registered",
            "低级键盘 hook 已接管热键",
            hotkeyKey=key,
            modifiers=parsed[0],
            virtualKey=parsed[1],
            itemCount=item_count,
        )
        return True

    def remove(self, key: int) -> None:
        with self._lock:
            self._items.pop(key, None)
            self._active.discard(key)
            item_count = len(self._items)
        _log().debug("hotkey.low_level_removed", "低级键盘 hook 移除热键", hotkeyKey=key, itemCount=item_count)

    def _ensure_started(self) -> None:
        with self._lock:
            if self._thread is not None:
                return
            ensure_started_at = perf_counter()
            self._thread = threading.Thread(target=self._run, name="win-hotkey-hook", daemon=True)
            self._thread.start()
        ready = self._ready.wait(1.0)
        _log().info(
            "hotkey.low_level_ensure_started",
            "低级键盘 hook 启动等待完成",
            ready=ready,
            available=self._available,
            elapsedMs=int((perf_counter() - ensure_started_at) * 1000),
        )

    def _run(self) -> None:
        ctypes.set_last_error(0)
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, kernel32.GetModuleHandleW(None), 0)
        self._available = bool(self._hook)
        if not self._available:
            _log().warning("hotkey.low_level_hook_failed", "低级键盘 hook 安装失败", errorCode=ctypes.get_last_error())
            self._ready.set()
            return
        _log().info("hotkey.low_level_hook_started", "低级键盘 hook 已启动")
        self._ready.set()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        user32.UnhookWindowsHookEx(self._hook)
        self._hook = None
        self._available = False

    def _callback(self, n_code: int, w_param: int, l_param: int) -> int:
        if n_code == HC_ACTION:
            event = int(w_param)
            if event in {WM_KEYDOWN, WM_SYSKEYDOWN, WM_KEYUP, WM_SYSKEYUP}:
                item = KBDLLHOOKSTRUCT.from_address(int(l_param))
                self._handle_key_event(
                    int(item.vkCode),
                    event in {WM_KEYDOWN, WM_SYSKEYDOWN},
                    bool(int(item.flags) & LLKHF_ALTDOWN),
                )
        return user32.CallNextHookEx(self._hook, n_code, w_param, l_param)

    def _handle_key_event(self, vk_code: int, pressed: bool, alt_down: bool = False) -> None:
        modifier = _modifier_from_vk(vk_code)
        if modifier:
            with self._lock:
                if pressed:
                    self._pressed_modifiers |= modifier
                else:
                    self._pressed_modifiers &= ~modifier
        with self._lock:
            items = list(self._items.items())
            modifiers = self._pressed_modifiers | _current_modifiers()
        if alt_down:
            modifiers |= MOD_ALT
        interested = bool(modifier) or any(vk_code == parsed[1] for _, (parsed, _) in items)
        if interested:
            _log().debug(
                "hotkey.low_level_key_event",
                "低级键盘 hook 收到相关按键",
                virtualKey=vk_code,
                pressed=pressed,
                modifiers=modifiers,
                itemCount=len(items),
            )
        if not pressed:
            with self._lock:
                for key, (parsed, _) in items:
                    if vk_code == parsed[1] or modifier:
                        self._active.discard(key)
            return
        for key, (parsed, callback) in items:
            expected_modifiers, expected_key = parsed
            if vk_code != expected_key or (modifiers & expected_modifiers) != expected_modifiers:
                if interested and pressed and vk_code == expected_key:
                    self._log_miss(key, expected_modifiers, expected_key, modifiers)
                continue
            with self._lock:
                if key in self._active:
                    _log().debug(
                        "hotkey.low_level_repeat_ignored",
                        "低级键盘 hook 忽略重复按下",
                        hotkeyKey=key,
                        virtualKey=vk_code,
                        modifiers=modifiers,
                    )
                    continue
                self._active.add(key)
            _log().info(
                "hotkey.low_level_match",
                "低级键盘 hook 匹配热键",
                hotkeyKey=key,
                virtualKey=vk_code,
                modifiers=modifiers,
            )
            callback()

    def _log_miss(self, key: int, expected_modifiers: int, expected_key: int, actual_modifiers: int) -> None:
        now = perf_counter()
        last = self._last_miss_log.get(key, 0.0)
        if now - last < 1.0:
            return
        self._last_miss_log[key] = now
        _log().debug(
            "hotkey.low_level_modifier_mismatch",
            "低级键盘 hook 收到目标键但修饰键不匹配",
            hotkeyKey=key,
            expectedModifiers=expected_modifiers,
            actualModifiers=actual_modifiers,
            expectedKey=expected_key,
        )


def _key_down(virtual_key: int) -> bool:
    return bool(user32.GetAsyncKeyState(virtual_key) & 0x8000)


def _current_modifiers() -> int:
    modifiers = 0
    if _key_down(VK_CONTROL):
        modifiers |= MOD_CONTROL
    if _key_down(VK_MENU):
        modifiers |= MOD_ALT
    if _key_down(VK_SHIFT):
        modifiers |= MOD_SHIFT
    if _key_down(VK_LWIN) or _key_down(VK_RWIN):
        modifiers |= MOD_WIN
    return modifiers


def _modifier_from_vk(virtual_key: int) -> int:
    if virtual_key in {VK_CONTROL, 0xA2, 0xA3}:
        return MOD_CONTROL
    if virtual_key in {VK_MENU, 0xA4, 0xA5}:
        return MOD_ALT
    if virtual_key in {VK_SHIFT, 0xA0, 0xA1}:
        return MOD_SHIFT
    if virtual_key in {VK_LWIN, VK_RWIN}:
        return MOD_WIN
    return 0


LOW_LEVEL_HOTKEY_HOOK = LowLevelHotkeyHook()


__all__ = ["LOW_LEVEL_HOTKEY_HOOK", "LowLevelHotkeyHook"]

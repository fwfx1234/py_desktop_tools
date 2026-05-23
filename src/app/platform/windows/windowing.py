from __future__ import annotations

import ctypes
from ctypes import wintypes


HWND_TOPMOST = wintypes.HWND(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.ShowWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowPos.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_uint,
]


def activate_window(window: object | None, *, force_top: bool = False) -> bool:
    hwnd = _hwnd(window)
    if not hwnd:
        return False
    activated = False
    if force_top:
        flags = SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        activated = bool(user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)) or activated
    else:
        flags = SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        activated = bool(user32.SetWindowPos(hwnd, wintypes.HWND(0), 0, 0, 0, 0, flags)) or activated
    activated = bool(user32.ShowWindow(hwnd, 5)) or activated
    activated = bool(user32.SetForegroundWindow(hwnd)) or activated
    return activated


def _hwnd(window: object | None) -> wintypes.HWND | None:
    if window is None:
        return None
    try:
        native_id = int(window.winId())
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None
    if not native_id:
        return None
    return wintypes.HWND(native_id)

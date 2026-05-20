from __future__ import annotations

__all__ = [
    "ClipboardBackend",
    "MacOSClipboardBackend",
    "NoopClipboardBackend",
    "PyperclipClipboardBackend",
    "Win32ClipboardBackend",
]


def __getattr__(name: str):
    if name == "ClipboardBackend":
        from .protocol import ClipboardBackend

        return ClipboardBackend
    if name == "MacOSClipboardBackend":
        from .macos_backend import MacOSClipboardBackend

        return MacOSClipboardBackend
    if name == "NoopClipboardBackend":
        from .noop_backend import NoopClipboardBackend

        return NoopClipboardBackend
    if name == "PyperclipClipboardBackend":
        from .pyperclip_backend import PyperclipClipboardBackend

        return PyperclipClipboardBackend
    if name == "Win32ClipboardBackend":
        from .win32_backend import Win32ClipboardBackend

        return Win32ClipboardBackend
    raise AttributeError(name)

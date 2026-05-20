from __future__ import annotations

from pathlib import Path

from app.platform.models import PlatformResult


class MacOSClipboardApi:
    def __init__(self, backend=None) -> None:
        if backend is None:
            try:
                from app.services.clipboard.backends.macos_backend import MacOSClipboardBackend

                backend = MacOSClipboardBackend()
            except Exception:
                from app.services.clipboard.backends.pyperclip_backend import PyperclipClipboardBackend

                backend = PyperclipClipboardBackend()
        self._backend = backend

    def read_text(self) -> str:
        try:
            return self._backend.read_text()
        except Exception:
            return ""

    def write_text(self, text: str) -> PlatformResult:
        try:
            self._backend.write_text(text)
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")
        return PlatformResult(True, data={"type": "text"})

    def write_files(self, paths: list[str | Path]) -> PlatformResult:
        clean_paths = [Path(path) for path in paths if str(path)]
        if not clean_paths:
            return PlatformResult(False, "文件列表为空", "invalid")
        missing = [str(path) for path in clean_paths if not path.exists()]
        if missing:
            return PlatformResult(False, "文件不存在", "not_found", {"missing": missing})
        try:
            self._backend.write_files([str(path) for path in clean_paths])
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")
        return PlatformResult(True, data={"type": "files", "count": len(clean_paths)})

    def clear(self) -> PlatformResult:
        try:
            self._backend.clear()
        except Exception as exc:
            return PlatformResult(False, str(exc), "failed")
        return PlatformResult(True)


__all__ = ["MacOSClipboardApi"]

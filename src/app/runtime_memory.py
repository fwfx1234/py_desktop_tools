from __future__ import annotations

import ctypes
import gc
import os
import sys
from ctypes import wintypes
from typing import Callable

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QTimer
from PySide6.QtQml import QQmlApplicationEngine

from app.logging import get_logger


CanClearCache = Callable[[], bool]


class RuntimeMemoryCleaner(QObject):
    """Run Qt/Python cleanup after plugin sessions have been destroyed."""

    def __init__(
        self,
        engine: QQmlApplicationEngine,
        qt_app: QObject,
        *,
        can_clear_component_cache: CanClearCache | None = None,
    ) -> None:
        parent = qt_app if isinstance(qt_app, QObject) else None
        super().__init__(parent)
        self._engine = engine
        self._can_clear_component_cache = can_clear_component_cache
        self._log = get_logger("app.runtime_memory")
        self._reasons: set[str] = set()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.run)

    def schedule(self, reason: str = "") -> None:
        if reason:
            self._reasons.add(reason)
        if not self._timer.isActive():
            self._timer.start(250)

    def run(self) -> None:
        reasons = sorted(self._reasons)
        self._reasons.clear()
        before = _process_memory_mb()
        can_clear = self._can_clear_component_cache() if self._can_clear_component_cache else False

        _flush_deferred_deletes()
        try:
            self._engine.collectGarbage()
        except RuntimeError:
            return
        try:
            if can_clear:
                self._engine.clearComponentCache()
            else:
                self._engine.trimComponentCache()
        except RuntimeError:
            return
        gc.collect()
        _flush_deferred_deletes()
        try:
            self._engine.collectGarbage()
        except RuntimeError:
            return

        if can_clear and _trim_working_set_enabled():
            _empty_working_set()

        after = _process_memory_mb()
        self._log.debug(
            "runtime.memory.cleanup",
            "运行时内存清理完成",
            reasons=",".join(reasons),
            componentCacheCleared=can_clear,
            beforeWorkingSetMb=before[0],
            beforePrivateMb=before[1],
            afterWorkingSetMb=after[0],
            afterPrivateMb=after[1],
        )


def _flush_deferred_deletes() -> None:
    app = QCoreApplication.instance()
    if app is None:
        return
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    QCoreApplication.processEvents()


def _trim_working_set_enabled() -> bool:
    value = os.getenv("PY_DESKTOP_TOOLS_TRIM_WORKING_SET", "").strip().lower()
    return value not in {"0", "false", "no", "off", "never"}


def _empty_working_set() -> None:
    if sys.platform != "win32":
        return
    try:
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi.EmptyWorkingSet.argtypes = [wintypes.HANDLE]
        psapi.EmptyWorkingSet.restype = wintypes.BOOL
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.EmptyWorkingSet(kernel32.GetCurrentProcess())
    except Exception:
        return


def _process_memory_mb() -> tuple[int, int]:
    if sys.platform != "win32":
        return (0, 0)
    try:
        class ProcessMemoryCountersEx(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t),
            ]

        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ProcessMemoryCountersEx),
            wintypes.DWORD,
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        counters = ProcessMemoryCountersEx()
        counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(
            kernel32.GetCurrentProcess(),
            ctypes.byref(counters),
            counters.cb,
        ):
            return (0, 0)
        return (
            round(counters.WorkingSetSize / 1024 / 1024),
            round(counters.PrivateUsage / 1024 / 1024),
        )
    except Exception:
        return (0, 0)

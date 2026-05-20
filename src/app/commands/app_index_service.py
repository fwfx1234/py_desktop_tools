from __future__ import annotations

from collections.abc import Callable
import hashlib
from time import perf_counter
from threading import Lock, Thread

from app.logging import get_logger
from app.commands.command_index_db import CommandIndexDb
from app.platform.services import PlatformServices


class AppIndexService:
    _SIGNATURE_KEY = "app_index_signature"
    _CHECK_INTERVAL_SECONDS = 5.0

    def __init__(self, index_db: CommandIndexDb, platform_services: PlatformServices) -> None:
        self._index_db = index_db
        self._platform = platform_services
        self._apps_scanned = False
        self._app_scan_running = False
        self._app_check_running = False
        self._last_check_started_at = 0.0
        self._shutdown = False
        self._app_scan_lock = Lock()
        self._index_lock = Lock()
        self._callbacks: list[Callable[[], None]] = []
        self._log = get_logger("app.commands.app_index_service")

    @property
    def index_lock(self) -> Lock:
        return self._index_lock

    @property
    def scan_running(self) -> bool:
        with self._app_scan_lock:
            return self._app_scan_running

    def on_scan_completed(self, callback: Callable[[], None]) -> None:
        self._callbacks.append(callback)

    def ensure_scan_started(self) -> None:
        if self.scan_running:
            return
        with self._index_lock:
            needs_scan = not self._apps_scanned and self._index_db.count_apps() == 0
        if needs_scan:
            self.start_scan()

    def start_change_check(self, *, force: bool = False) -> bool:
        now = perf_counter()
        with self._app_scan_lock:
            if self._shutdown or self._app_scan_running or self._app_check_running:
                return False
            if not force and now - self._last_check_started_at < self._CHECK_INTERVAL_SECONDS:
                return False
            self._app_check_running = True
            self._last_check_started_at = now

        def run_check() -> None:
            try:
                started_at = perf_counter()
                signature = self._current_signature()
                with self._index_lock:
                    if self._shutdown:
                        return
                    previous = self._index_db.get_app_index_meta(self._SIGNATURE_KEY)
                    app_count = self._index_db.count_apps()
                changed = app_count == 0 or not previous or previous != signature
                self._log.debug(
                    "command.app_check.complete",
                    "应用索引变更检查完成",
                    changed=changed,
                    appCount=app_count,
                    elapsedMs=int((perf_counter() - started_at) * 1000),
                )
                if changed:
                    self.start_scan(force=True)
                else:
                    self._apps_scanned = True
            except Exception as exc:
                self._log.warning("command.app_check_failed", "应用索引变更检查失败", error=str(exc))
            finally:
                with self._app_scan_lock:
                    self._app_check_running = False

        Thread(target=run_check, name="app-index-check", daemon=True).start()
        return True

    def start_scan(self, *, force: bool = False) -> bool:
        with self._app_scan_lock:
            if self._shutdown:
                return False
            if self._app_scan_running:
                return False
            if self._apps_scanned and not force:
                return False
            self._app_scan_running = True

        def run_scan() -> None:
            notified = False
            try:
                metadata_started_at = perf_counter()
                apps = self._platform.app_indexer.scan_apps(
                    None,
                    extract_icons=False,
                )
                signature = self._current_signature()
                with self._index_lock:
                    if self._shutdown:
                        return
                    self._index_db.sync_apps([app.to_db_dict() for app in apps])
                    self._index_db.set_app_index_meta(self._SIGNATURE_KEY, signature)
                self._apps_scanned = True
                self._log.debug(
                    "command.app_scan.complete",
                    "应用索引扫描完成",
                    count=len(apps),
                    iconScan=False,
                    elapsedMs=int((perf_counter() - metadata_started_at) * 1000),
                )
                self._notify_callbacks()
                notified = True
                if not apps:
                    return

                icon_started_at = perf_counter()
                apps_with_icons = self._platform.app_indexer.scan_apps(
                    self._index_db.get_icon_dir(),
                    extract_icons=True,
                )
                if apps_with_icons:
                    with self._index_lock:
                        if self._shutdown:
                            return
                        self._index_db.sync_apps([app.to_db_dict() for app in apps_with_icons])
                    self._log.debug(
                        "command.app_icon_scan.complete",
                        "应用图标索引扫描完成",
                        count=len(apps_with_icons),
                        iconCount=sum(1 for app in apps_with_icons if app.icon_path),
                        elapsedMs=int((perf_counter() - icon_started_at) * 1000),
                    )
                    self._notify_callbacks()
                    notified = True
            except Exception as exc:
                self._log.warning("command.app_scan_failed", "应用索引扫描失败", error=str(exc))
            finally:
                with self._app_scan_lock:
                    self._app_scan_running = False
                if not notified:
                    self._notify_callbacks()

        Thread(target=run_scan, name="app-index-scan", daemon=True).start()
        return True

    def shutdown(self) -> None:
        with self._app_scan_lock:
            self._shutdown = True
        with self._index_lock:
            return

    def _notify_callbacks(self) -> None:
        with self._app_scan_lock:
            if self._shutdown:
                return
        for callback in list(self._callbacks):
            try:
                callback()
            except Exception as exc:
                self._log.warning("command.app_scan_callback_failed", "应用索引扫描回调失败", error=str(exc))

    def _current_signature(self) -> str:
        quick_signature = getattr(self._platform.app_indexer, "quick_signature", None)
        if callable(quick_signature):
            return str(quick_signature())
        apps = self._platform.app_indexer.scan_apps(None, extract_icons=False)
        return _signature_from_apps([app.to_db_dict() for app in apps])


def _signature_from_apps(apps: list[dict]) -> str:
    digest = hashlib.sha256()
    for app in sorted(apps, key=lambda item: str(item.get("launch_path") or "")):
        digest.update(str(app.get("platform") or "").encode("utf-8", errors="ignore"))
        digest.update(b"\0")
        digest.update(str(app.get("launch_path") or "").encode("utf-8", errors="ignore"))
        digest.update(b"\0")
        digest.update(str(app.get("bundle_id") or "").encode("utf-8", errors="ignore"))
        digest.update(b"\0")
    return f"apps:{len(apps)}:{digest.hexdigest()}"

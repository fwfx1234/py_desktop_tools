from __future__ import annotations

import os
from pathlib import Path
from time import perf_counter
from typing import Any

from PySide6.QtCore import QFileSystemWatcher, QObject, QTimer, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from .app_bootstrap import ApplicationBootstrapper


class QmlHotReloader(QObject):
    def __init__(
        self,
        engine: QQmlApplicationEngine,
        qml_files: list[Path],
        watch_root: Path,
    ) -> None:
        super().__init__()
        self._engine = engine
        self._qml_files = qml_files
        self._watch_root = watch_root
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)
        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.setInterval(180)
        self._reload_timer.timeout.connect(self._reload)
        self._refresh_watch_files()

    def _all_qml_files(self) -> list[str]:
        return [str(path) for path in self._watch_root.rglob("*.qml") if path.is_file()]

    def _refresh_watch_files(self) -> None:
        current = set(self._watcher.files())
        desired = set(self._all_qml_files())
        to_remove = list(current - desired)
        to_add = [path for path in (desired - current) if Path(path).exists()]
        if to_remove:
            self._watcher.removePaths(to_remove)
        if to_add:
            self._watcher.addPaths(to_add)

    def _on_file_changed(self, _path: str) -> None:
        self._refresh_watch_files()
        self._reload_timer.start()

    def _reload(self) -> None:
        old_roots = list(self._engine.rootObjects())
        self._engine.clearComponentCache()
        for qml_file in self._qml_files:
            self._engine.load(QUrl.fromLocalFile(str(qml_file)))
        new_roots = self._engine.rootObjects()
        if len(new_roots) > len(old_roots):
            for root in old_roots:
                root.deleteLater()
        self._refresh_watch_files()


class ApplicationRuntime:
    def __init__(self, qt_app: QApplication, log: Any) -> None:
        self._qt_app = qt_app
        self._log = log

    def run(self) -> int:
        build_started_at = perf_counter()
        app_context = ApplicationBootstrapper(self._qt_app, self._log).build()
        build_elapsed_ms = int((perf_counter() - build_started_at) * 1000)
        if app_context is None:
            self._log.error("app.bootstrap.failed", "应用启动上下文创建失败", elapsedMs=build_elapsed_ms)
            return 1
        self._log.info("app.bootstrap.complete", "应用启动上下文创建完成", elapsedMs=build_elapsed_ms)
        start_started_at = perf_counter()
        app_context.start()
        self._log.debug("app.context.start_complete", "应用上下文启动完成", elapsedMs=int((perf_counter() - start_started_at) * 1000))

        if os.getenv("PY_DESKTOP_QML_HOT_RELOAD", "").strip() in {"1", "true", "TRUE"}:
            hot_reload_started_at = perf_counter()
            hot_reloader = QmlHotReloader(
                app_context.engine,
                [app_context.main_qml, app_context.plugin_window_qml],
                Path(__file__).parents[1],
            )
            self._qt_app.setProperty("_qmlHotReloader", hot_reloader)
            self._log.info(
                "app.qml_hot_reload_enabled",
                "启用 QML 热重载",
                elapsedMs=int((perf_counter() - hot_reload_started_at) * 1000),
            )

        self._qt_app.setProperty("_applicationContext", app_context)
        exec_started_at = perf_counter()
        self._log.debug("app.event_loop.start", "进入 Qt 事件循环")
        code = self._qt_app.exec()
        self._log.info("app.exit", "应用退出", exitCode=code, elapsedMs=int((perf_counter() - exec_started_at) * 1000))
        return code

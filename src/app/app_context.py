from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from random import randint
from time import perf_counter
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from app.application_controller import ApplicationController
from app.app_view_model import AppViewModel
from app.commands.command_index_db import CommandIndexDb
from app.commands.command_service import CommandService
from app.commands.dynamic_command_registry import DynamicCommandRegistry
from app.hotkeys import HotkeyLifecycle
from app.launcher.launcher_bridge import LauncherBridge
from app.launcher.launcher_window import LauncherWindowController
from app.platform.services import PlatformServices
from app.plugins.background_manager import BackgroundManager
from app.plugins.manifest import PluginManifest
from app.plugins.manifest_loader import load_all_plugin_manifests
from app.plugins.host import PluginHostService
from app.plugins.plugin_manager import PluginManager
from app.plugins.runtime import PluginContext
from app.plugins.session_manager import PluginSessionManager
from app.runtime_memory import RuntimeMemoryCleaner
from app.storage import StorageManager
from app.tray.service import TrayService


@dataclass(slots=True, weakref_slot=True)
class ApplicationContext:
    qt_app: QApplication
    log: Any
    app_dir: Path
    main_qml: Path
    plugin_window_qml: Path
    engine: QQmlApplicationEngine
    app_vm: AppViewModel
    platform_services: PlatformServices
    storage: StorageManager
    dynamic_commands: DynamicCommandRegistry
    command_index: CommandIndexDb
    manifests: list[PluginManifest]
    plugin_manager: PluginManager
    plugin_context: PluginContext
    background_manager: BackgroundManager
    command_service: CommandService
    launcher_bridge: LauncherBridge
    session_manager: PluginSessionManager
    plugin_host: PluginHostService
    app_controller: ApplicationController
    hotkey_lifecycle: HotkeyLifecycle
    tray_service: TrayService
    launcher_window_controller: LauncherWindowController
    launcher_window: object | None = None
    runtime_memory: RuntimeMemoryCleaner | None = None
    _shutting_down: bool = field(default=False, init=False)
    _app_index_refresh_timer: QTimer | None = field(default=None, init=False)
    _background_plugins_started: bool = field(default=False, init=False)

    def start(self) -> None:
        started_at = perf_counter()
        connect_started_at = perf_counter()
        self.app_controller.connect()
        self.log.debug("app.context.signals_connected", "运行信号连接完成", elapsedMs=int((perf_counter() - connect_started_at) * 1000))
        hotkeys_started_at = perf_counter()
        self.hotkey_lifecycle.install()
        self.log.debug("app.context.hotkeys_install_scheduled", "热键安装已调度", elapsedMs=int((perf_counter() - hotkeys_started_at) * 1000))
        self.qt_app.aboutToQuit.connect(self.shutdown)
        tray_started_at = perf_counter()
        self.tray_service.show()
        self.log.debug("app.context.tray_show_complete", "系统托盘显示完成", elapsedMs=int((perf_counter() - tray_started_at) * 1000))
        QTimer.singleShot(100, self._start_background_plugins)
        if self.launcher_window_controller.prewarm_enabled() and not self._is_macos():
            QTimer.singleShot(3000, self.launcher_window_controller.prewarm)
            self.log.debug("launcher.prewarm_scheduled", "启动器窗口预热已调度", delayMs=3000)
        QTimer.singleShot(250, self._start_initial_app_index_scan)
        self._schedule_app_index_refresh()
        self.log.debug("app.context.start_scheduled", "后台插件启动已调度", elapsedMs=int((perf_counter() - started_at) * 1000))

    def shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        if self._app_index_refresh_timer is not None:
            self._app_index_refresh_timer.stop()
            self._app_index_refresh_timer.deleteLater()
            self._app_index_refresh_timer = None
        self.hotkey_lifecycle.shutdown()
        self.plugin_host.destroy_all()
        self.session_manager.close_all()
        self.background_manager.stop_all()
        self.plugin_manager.close_all()
        self.command_service.shutdown()
        self.command_index.close()
        if self.runtime_memory is not None:
            self.runtime_memory.run()

    def reload_plugins(self) -> list[PluginManifest]:
        manifests = load_all_plugin_manifests()
        self.background_manager.stop_removed(manifests)
        self.manifests = manifests
        self.plugin_manager.replace_manifests(manifests)
        self.command_service.replace_manifests(manifests)
        self.background_manager.refresh_manifests(manifests)
        self.hotkey_lifecycle.refresh_manifests(manifests)
        self.app_controller.refresh_manifests(manifests)
        return manifests

    def _start_background_plugins(self) -> None:
        if self._shutting_down:
            return
        if self._background_plugins_started:
            return
        self._background_plugins_started = True
        self.background_manager.start_all()
        self.hotkey_lifecycle.connect_clipboard_config()
        if self.hotkey_lifecycle.is_registered():
            self.hotkey_lifecycle.refresh_clipboard_hotkey()

    def _start_initial_app_index_scan(self) -> None:
        if self._shutting_down:
            return
        started = self.command_service.check_app_index_changes(force=True)
        self.log.debug("app.index.initial_check", "应用索引初始检查已调度", started=started)

    def _schedule_app_index_refresh(self) -> None:
        if self._shutting_down:
            return
        if self._app_index_refresh_timer is None:
            self._app_index_refresh_timer = QTimer()
            self._app_index_refresh_timer.setSingleShot(True)
            self._app_index_refresh_timer.timeout.connect(self._refresh_app_index_in_background)
        interval_ms = randint(20 * 60_000, 45 * 60_000)
        self._app_index_refresh_timer.start(interval_ms)
        self.log.debug("app.index.refresh_scheduled", "后台应用索引刷新已调度", intervalMs=interval_ms)

    def _refresh_app_index_in_background(self) -> None:
        if self._shutting_down:
            return
        started = self.command_service.check_app_index_changes(force=True)
        self.log.debug("app.index.background_check", "后台应用索引检查已触发", started=started)
        self._schedule_app_index_refresh()

    def _is_macos(self) -> bool:
        return getattr(self.platform_services.info, "name", "") == "macos"

from __future__ import annotations

from time import perf_counter
from typing import Any

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from app.app_context import ApplicationContext
from app.app_view_model import AppViewModel
from app.commands.command_index_db import CommandIndexDb
from app.commands.command_service import CommandService
from app.commands.dynamic_command_registry import DynamicCommandRegistry
from app.launcher.launcher_bridge import LauncherBridge
from app.launcher_runtime_coordinator import LauncherRuntimeCoordinator
from app.platform.factory import create_platform_services
from app.plugin_surface_coordinator import PluginSurfaceCoordinator
from app.plugins.background_manager import BackgroundManager
from app.plugins.manifest_loader import load_all_plugin_manifests
from app.plugins.plugin_manager import PluginManager
from app.plugins.runtime import PluginContext
from app.plugins.service_registry import ServiceRegistry
from app.plugins.session_manager import PluginSessionManager
from app.qta_icon_provider import QtAwesomeImageProvider
from app.paths import resource_root
from app.storage import StorageManager
from app.tray_coordinator import TrayCoordinator


class ApplicationBootstrapper:
    def __init__(self, qt_app: QApplication, log: Any) -> None:
        self._qt_app = qt_app
        self._log = log

    def build(self) -> ApplicationContext | None:
        total_started_at = perf_counter()
        engine_started_at = perf_counter()
        engine = QQmlApplicationEngine()
        engine.addImageProvider("qta", QtAwesomeImageProvider())
        self._log.debug("app.bootstrap.engine_ready", "QML 引擎初始化完成", elapsedMs=int((perf_counter() - engine_started_at) * 1000))

        app_vm_started_at = perf_counter()
        app_vm = AppViewModel()
        qml_context = engine.rootContext()
        qml_context.setContextProperty("app", app_vm)
        self._log.debug("app.bootstrap.app_vm_ready", "AppViewModel 初始化完成", elapsedMs=int((perf_counter() - app_vm_started_at) * 1000))

        services_started_at = perf_counter()
        storage = StorageManager()
        dynamic_commands = DynamicCommandRegistry()
        platform_services = create_platform_services(
            self._qt_app,
            storage=storage,
            dynamic_commands=dynamic_commands,
        )
        app_vm.setPlatform(platform_services.info.name, platform_services.info.display_name)
        platform_api = platform_services.create_api()
        command_index = CommandIndexDb(
            storage.database("command_index.db", wal=True, check_same_thread=False)
        )
        self._log.debug("app.bootstrap.services_ready", "平台服务和存储初始化完成", elapsedMs=int((perf_counter() - services_started_at) * 1000))
        manifests_started_at = perf_counter()
        manifests = load_all_plugin_manifests()
        self._log.debug("app.plugins.loaded", "插件清单加载完成", count=len(manifests), elapsedMs=int((perf_counter() - manifests_started_at) * 1000))

        managers_started_at = perf_counter()
        plugin_manager = PluginManager(manifests)
        command_service = CommandService(
            manifests,
            command_index,
            dynamic_commands,
            platform_services=platform_services,
        )
        plugin_context = PluginContext(
            command_index=command_index,
            command_service=command_service,
            platform=platform_api,
            services=ServiceRegistry(
                platform=platform_api,
                storage=storage,
            ),
        )
        background_manager = BackgroundManager(manifests, plugin_manager, plugin_context)
        launcher_bridge = LauncherBridge(command_service, plugin_context.services)
        qml_context.setContextProperty("launcherBridge", launcher_bridge)
        self._log.debug("app.bootstrap.managers_ready", "插件和命令管理器初始化完成", elapsedMs=int((perf_counter() - managers_started_at) * 1000))

        app_dir = resource_root() / "src" / "app"
        main_qml = app_dir / "Main.qml"
        plugin_window_qml = app_dir / "launcher" / "PluginWindow.qml"
        qml_started_at = perf_counter()
        engine.load(QUrl.fromLocalFile(str(main_qml)))
        if not engine.rootObjects():
            self._log.error("app.bootstrap.qml_load_failed", "主 QML 加载失败", qmlPath=str(main_qml), elapsedMs=int((perf_counter() - qml_started_at) * 1000))
            command_index.close()
            return None
        self._log.debug(
            "app.bootstrap.qml_loaded",
            "主 QML 加载完成",
            qmlPath=str(main_qml),
            rootCount=len(engine.rootObjects()),
            elapsedMs=int((perf_counter() - qml_started_at) * 1000),
        )

        coordinators_started_at = perf_counter()
        launcher_window = self._find_launcher_window(engine)
        coordinator_ref: dict[str, LauncherRuntimeCoordinator] = {}

        def on_retention_expired(plugin_id: str, state) -> None:
            coordinator = coordinator_ref.get("coordinator")
            if coordinator is not None:
                coordinator.on_retention_expired(plugin_id, state)
                return
            session_manager.unload_plugin(plugin_id)

        def on_retained_close(plugin_id: str, host: str) -> None:
            coordinator = coordinator_ref.get("coordinator")
            if coordinator is not None:
                coordinator.on_surface_retained_close(plugin_id, host)

        session_manager = PluginSessionManager(
            qml_context,
            plugin_manager,
            plugin_context,
            on_retention_expired=on_retention_expired,
        )
        surface_coordinator = PluginSurfaceCoordinator(
            engine,
            self._qt_app,
            plugin_window_qml_path=str(plugin_window_qml),
            app_dir=app_dir,
            launcher_bridge=launcher_bridge,
            launcher_window=launcher_window,
            on_retained_close=on_retained_close,
        )
        runtime_coordinator = LauncherRuntimeCoordinator(
            qt_app=self._qt_app,
            platform_services=platform_services,
            manifests=manifests,
            plugin_context=plugin_context,
            background_manager=background_manager,
            session_manager=session_manager,
            surface_coordinator=surface_coordinator,
            launcher_bridge=launcher_bridge,
            launcher_window=launcher_window,
            on_quit=self._qt_app.quit,
        )
        coordinator_ref["coordinator"] = runtime_coordinator
        tray_coordinator = TrayCoordinator(
            parent=self._qt_app,
            on_show_window=runtime_coordinator.toggle_launcher,
            on_restart=runtime_coordinator.restart_app,
            on_quit=self._qt_app.quit,
        )
        self._log.debug(
            "app.bootstrap.coordinators_ready",
            "运行协调器初始化完成",
            launcherWindowFound=launcher_window is not None,
            elapsedMs=int((perf_counter() - coordinators_started_at) * 1000),
        )

        self._log.debug("app.bootstrap.build_ready", "应用启动上下文组装完成", elapsedMs=int((perf_counter() - total_started_at) * 1000))
        return ApplicationContext(
            qt_app=self._qt_app,
            log=self._log,
            app_dir=app_dir,
            main_qml=main_qml,
            plugin_window_qml=plugin_window_qml,
            engine=engine,
            app_vm=app_vm,
            platform_services=platform_services,
            storage=storage,
            dynamic_commands=dynamic_commands,
            command_index=command_index,
            manifests=manifests,
            plugin_manager=plugin_manager,
            plugin_context=plugin_context,
            background_manager=background_manager,
            command_service=command_service,
            launcher_bridge=launcher_bridge,
            session_manager=session_manager,
            surface_coordinator=surface_coordinator,
            runtime_coordinator=runtime_coordinator,
            tray_coordinator=tray_coordinator,
            launcher_window=launcher_window,
        )

    @staticmethod
    def _find_launcher_window(engine: QQmlApplicationEngine) -> object | None:
        for root_obj in engine.rootObjects():
            if root_obj.objectName() == "launcherWindow":
                return root_obj
        return None

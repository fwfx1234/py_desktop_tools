from __future__ import annotations

from time import perf_counter
from typing import Any

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from app.app_context import ApplicationContext
from app.application_controller import ApplicationController
from app.app_view_model import AppViewModel
from app.commands.command_index_db import CommandIndexDb
from app.commands.command_service import CommandService
from app.commands.dynamic_command_registry import DynamicCommandRegistry
from app.hotkeys import HotkeyLifecycle, HotkeyService
from app.launcher.launcher_bridge import LauncherBridge
from app.launcher.launcher_window import LauncherWindowController
from app.platform.factory import create_platform_services
from app.plugins.background_manager import BackgroundManager
from app.plugins.host import PluginHostService
from app.plugins.manifest_loader import load_all_plugin_manifests
from app.plugins.plugin_manager import PluginManager
from app.plugins.runtime import PluginContext
from app.plugins.service_registry import ServiceRegistry
from app.plugins.session_manager import PluginSessionManager
from app.runtime_memory import RuntimeMemoryCleaner
from app.qta_icon_provider import QtAwesomeImageProvider
from app.paths import resource_root
from app.plugins.importer import import_plugin_package, imported_plugin_root
from app.storage import StorageManager
from app.tray.service import TrayService


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
        context_ref: dict[str, ApplicationContext] = {}

        def import_plugins(source: str) -> dict:
            result = import_plugin_package(source)
            if result.ok and context_ref.get("context") is not None:
                context_ref["context"].reload_plugins()
            return result.to_dict()

        plugin_context.services.plugin_importer = import_plugins
        plugin_context.services.imported_plugin_root = imported_plugin_root
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

        app_services_started_at = perf_counter()
        launcher_window = self._find_launcher_window(engine)
        controller_ref: dict[str, ApplicationController] = {}
        launcher_window_controller = LauncherWindowController(
            qt_app=self._qt_app,
            platform_services=platform_services,
            launcher_window=launcher_window,
        )

        def on_retention_expired(plugin_id: str, state) -> None:
            controller = controller_ref.get("controller")
            if controller is not None:
                controller.on_retention_expired(plugin_id, state)
                return
            session_manager.unload_plugin(plugin_id)

        def on_retained_close(plugin_id: str, host: str) -> None:
            controller = controller_ref.get("controller")
            if controller is not None:
                controller.on_surface_retained_close(plugin_id, host)

        session_manager = PluginSessionManager(
            qml_context,
            plugin_manager,
            plugin_context,
            on_retention_expired=on_retention_expired,
        )
        plugin_host = PluginHostService(
            engine,
            self._qt_app,
            plugin_window_qml_path=str(plugin_window_qml),
            app_dir=app_dir,
            launcher_bridge=launcher_bridge,
            launcher_window=launcher_window,
            on_retained_close=on_retained_close,
        )
        runtime_memory = RuntimeMemoryCleaner(
            engine,
            self._qt_app,
            can_clear_component_cache=lambda: not session_manager.has_sessions(),
        )
        session_manager.set_memory_cleanup(runtime_memory.schedule)
        app_controller = ApplicationController(
            session_manager=session_manager,
            plugin_host=plugin_host,
            launcher_bridge=launcher_bridge,
            launcher_window_controller=launcher_window_controller,
            on_quit=self._qt_app.quit,
        )
        controller_ref["controller"] = app_controller
        hotkey_service = HotkeyService(
            platform_services,
            self._qt_app,
            on_launcher_toggle=app_controller.toggle_launcher,
            on_clipboard_toggle=app_controller.open_clipboard_history,
            on_plugin_launched=app_controller.open_plugin,
        )
        hotkey_lifecycle = HotkeyLifecycle(
            qt_app=self._qt_app,
            manifests=manifests,
            platform_services=platform_services,
            plugin_context=plugin_context,
            launcher_window_controller=launcher_window_controller,
            hotkey_service=hotkey_service,
        )
        tray_service = TrayService(
            parent=self._qt_app,
            on_show_window=app_controller.toggle_launcher,
            on_restart=app_controller.restart_app,
            on_quit=self._qt_app.quit,
        )
        self._log.debug(
            "app.bootstrap.app_services_ready",
            "应用运行服务初始化完成",
            launcherWindowFound=launcher_window is not None,
            elapsedMs=int((perf_counter() - app_services_started_at) * 1000),
        )

        self._log.debug("app.bootstrap.build_ready", "应用启动上下文组装完成", elapsedMs=int((perf_counter() - total_started_at) * 1000))
        app_context = ApplicationContext(
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
            plugin_host=plugin_host,
            app_controller=app_controller,
            hotkey_lifecycle=hotkey_lifecycle,
            tray_service=tray_service,
            launcher_window_controller=launcher_window_controller,
            launcher_window=launcher_window,
            runtime_memory=runtime_memory,
        )
        context_ref["context"] = app_context
        return app_context

    @staticmethod
    def _find_launcher_window(engine: QQmlApplicationEngine) -> object | None:
        for root_obj in engine.rootObjects():
            if root_obj.objectName() == "launcherWindow":
                return root_obj
        return None

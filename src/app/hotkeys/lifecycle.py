from __future__ import annotations

from time import perf_counter

from PySide6.QtCore import QTimer

from app.hotkeys.service import HotkeyService
from app.launcher.launcher_window import LauncherWindowController
from app.logging import get_logger
from app.platform.services import PlatformServices
from app.plugins.manifest import PluginManifest
from app.plugins.runtime import PluginContext
from app.services.clipboard import DEFAULT_CLIPBOARD_CONFIG
from app.storage import StorageManager


class ClipboardHotkeyProvider:
    def __init__(
        self,
        *,
        platform_services: PlatformServices,
        plugin_context: PluginContext,
    ) -> None:
        self._platform_services = platform_services
        self._plugin_context = plugin_context

    def current_hotkey(self) -> str:
        default_hotkey = str(
            self._platform_services.default_clipboard_hotkey
            or DEFAULT_CLIPBOARD_CONFIG.get("hotkey")
            or "Alt+V"
        )
        service = getattr(self._plugin_context.services, "clipboard", None)
        if service is not None:
            get_config_value = getattr(service, "get_config_value", None)
            if callable(get_config_value):
                hotkey = str(get_config_value("hotkey") or "").strip()
                if hotkey:
                    return hotkey
            store = getattr(service, "store", None)
            if store is not None:
                hotkey = str(store.get_config_value("hotkey") or "").strip()
                if hotkey:
                    return hotkey
        storage = getattr(self._plugin_context.services, "storage", None)
        if isinstance(storage, StorageManager):
            try:
                hotkey = str(
                    storage.dict_store(
                        "clipboard/settings",
                        defaults=DEFAULT_CLIPBOARD_CONFIG,
                    ).get("hotkey")
                    or ""
                ).strip()
            except Exception:
                hotkey = ""
            if hotkey:
                return hotkey
        return default_hotkey


class HotkeyLifecycle:
    def __init__(
        self,
        *,
        qt_app: object,
        manifests: list[PluginManifest],
        platform_services: PlatformServices,
        plugin_context: PluginContext,
        launcher_window_controller: LauncherWindowController,
        hotkey_service: HotkeyService,
    ) -> None:
        self._qt_app = qt_app
        self._manifests = manifests
        self._plugin_context = plugin_context
        self._launcher_window_controller = launcher_window_controller
        self._hotkey_service = hotkey_service
        self._clipboard_hotkey_provider = ClipboardHotkeyProvider(
            platform_services=platform_services,
            plugin_context=plugin_context,
        )
        self._log = get_logger("app.hotkeys.lifecycle")
        self._registered = False
        self._clipboard_config_connected = False
        self._shutting_down = False

    def install(self) -> None:
        if self._shutting_down:
            return
        started_at = perf_counter()
        filters = self._hotkey_service.root_filters()
        self._qt_app.setProperty("_hotkeyFilters", filters)
        self._log.debug(
            "hotkey.install_filters",
            "安装全局热键事件过滤器",
            filterCount=len(filters),
            elapsedMs=int((perf_counter() - started_at) * 1000),
        )
        QTimer.singleShot(500, self.register)
        self._log.debug("hotkey.register_scheduled", "全局热键注册已调度", delayMs=500)

    def shutdown(self) -> None:
        self._shutting_down = True
        self._hotkey_service.unregister_all()

    def register(self) -> None:
        if self._shutting_down:
            return
        started_at = perf_counter()
        hwnd = self._launcher_window_controller.window_id()
        if hwnd:
            self._launcher_window_controller.configure_for_macos()
        self._log.debug(
            "hotkey.register_begin",
            "开始注册全局热键",
            launcherWindowFound=self._launcher_window_controller.is_available(),
            launcherHwnd=hwnd,
        )
        if hwnd:
            self._hotkey_service.assign_hwnd(hwnd)
        self._hotkey_service.register_all(
            self._manifests,
            clipboard_hotkey=self._clipboard_hotkey_provider.current_hotkey(),
        )
        self._registered = True
        property_started_at = perf_counter()
        self._qt_app.setProperty("_pluginHotkeyFilters", self._hotkey_service.plugin_filters())
        self._log.debug(
            "hotkey.register_end",
            "全局热键注册流程完成",
            pluginFilterCount=len(self._hotkey_service.plugin_filters()),
            propertyElapsedMs=int((perf_counter() - property_started_at) * 1000),
            elapsedMs=int((perf_counter() - started_at) * 1000),
        )

    def connect_clipboard_config(self) -> None:
        if self._clipboard_config_connected or self._shutting_down:
            return
        clipboard_service = getattr(self._plugin_context.services, "clipboard", None)
        if clipboard_service is None:
            return
        add_listener = getattr(clipboard_service, "add_config_listener", None)
        if callable(add_listener):
            add_listener(self.refresh_clipboard_hotkey)
            self._clipboard_config_connected = True
            return
        clipboard_store = getattr(clipboard_service, "store", None)
        config_changed = getattr(clipboard_store, "configChanged", None)
        connect = getattr(config_changed, "connect", None)
        if callable(connect):
            connect(self.refresh_clipboard_hotkey)
            self._clipboard_config_connected = True

    def refresh_clipboard_hotkey(self) -> None:
        if self._shutting_down:
            return
        self._log.debug("hotkey.clipboard_refresh", "刷新剪贴板热键")
        self._hotkey_service.refresh_clipboard_hotkey(
            self._clipboard_hotkey_provider.current_hotkey()
        )

    def refresh_manifests(self, manifests: list[PluginManifest]) -> None:
        self._manifests = manifests
        if self._registered and not self._shutting_down:
            self._hotkey_service.refresh_plugin_hotkeys(manifests)
            self._qt_app.setProperty("_pluginHotkeyFilters", self._hotkey_service.plugin_filters())

    def is_registered(self) -> bool:
        return self._registered

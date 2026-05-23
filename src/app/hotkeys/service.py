"""Manages launcher, clipboard, and plugin hotkeys."""

from __future__ import annotations

from time import perf_counter

from app.logging import get_logger
from app.platform.services import PlatformServices
from app.plugins.manifest import PluginManifest


class HotkeyService:
    def __init__(
        self,
        platform_services: PlatformServices,
        qt_app: object,
        *,
        on_launcher_toggle: object = None,
        on_clipboard_toggle: object = None,
        on_plugin_launched: object = None,
    ) -> None:
        self._platform = platform_services
        self._qt_app = qt_app
        self._on_launcher_toggle = on_launcher_toggle
        self._on_clipboard_toggle = on_clipboard_toggle
        self._on_plugin_launched = on_plugin_launched
        self._log = get_logger("app.hotkeys")

        self._launcher_mgr = platform_services.hotkey_factory.create(
            parent=qt_app,
            hotkey=platform_services.default_launcher_hotkey,
            hotkey_id=1,
        )
        self._clipboard_mgr = platform_services.hotkey_factory.create(
            parent=qt_app,
            hotkey=platform_services.default_clipboard_hotkey,
            hotkey_id=2,
        )
        self._plugin_managers: list[object] = []
        self._plugin_filters: list[object] = []
        self._hwnd = 0
        if self._on_launcher_toggle is not None:
            self._launcher_mgr.hotkeyPressed.connect(self._on_launcher_toggle)
        if self._on_clipboard_toggle is not None:
            self._clipboard_mgr.hotkeyPressed.connect(self._on_clipboard_toggle)

    @property
    def launcher_manager(self) -> object:
        return self._launcher_mgr

    @property
    def clipboard_manager(self) -> object:
        return self._clipboard_mgr

    def assign_hwnd(self, hwnd: int) -> None:
        self._hwnd = hwnd
        for mgr in [self._launcher_mgr, self._clipboard_mgr, *self._plugin_managers]:
            set_hwnd = getattr(mgr, "set_hwnd", None)
            if callable(set_hwnd):
                set_hwnd(hwnd)

    def register_all(self, manifests: list[PluginManifest] | None = None, *, clipboard_hotkey: str = "") -> None:
        started_at = perf_counter()
        launcher_started_at = perf_counter()
        if not self._launcher_mgr.register():
            self._log.warning(
                "hotkey.register_failed",
                "全局热键注册失败",
                hotkey=self._platform.default_launcher_hotkey,
                errorCode=getattr(self._launcher_mgr, "last_error", 0),
                elapsedMs=int((perf_counter() - launcher_started_at) * 1000),
            )
        else:
            self._log.debug(
                "hotkey.registered",
                "全局热键注册成功",
                hotkey=self._platform.default_launcher_hotkey,
                hotkeyId=getattr(self._launcher_mgr, "hotkey_id", 0),
                nativeRegistered=getattr(self._launcher_mgr, "native_registered", None),
                fallbackRegistered=getattr(self._launcher_mgr, "fallback_registered", None),
                elapsedMs=int((perf_counter() - launcher_started_at) * 1000),
            )
        clipboard_started_at = perf_counter()
        self.refresh_clipboard_hotkey(clipboard_hotkey or self._platform.default_clipboard_hotkey)
        clipboard_elapsed_ms = int((perf_counter() - clipboard_started_at) * 1000)
        plugins_started_at = perf_counter()
        self.refresh_plugin_hotkeys(manifests or [])
        self._log.debug(
            "hotkey.register_all_complete",
            "全部热键注册流程完成",
            manifestCount=len(manifests or []),
            clipboardElapsedMs=clipboard_elapsed_ms,
            pluginElapsedMs=int((perf_counter() - plugins_started_at) * 1000),
            elapsedMs=int((perf_counter() - started_at) * 1000),
        )

    def refresh_clipboard_hotkey(self, hotkey: str) -> None:
        started_at = perf_counter()
        self._clipboard_mgr.unregister()
        if not hotkey:
            self._log.debug("hotkey.clipboard_disabled", "剪贴板热键为空，跳过注册", elapsedMs=int((perf_counter() - started_at) * 1000))
            return
        if not self._clipboard_mgr.register(hotkey):
            self._log.warning(
                "hotkey.clipboard_register_failed",
                "剪贴板热键注册失败",
                hotkey=hotkey,
                errorCode=getattr(self._clipboard_mgr, "last_error", 0),
                elapsedMs=int((perf_counter() - started_at) * 1000),
            )
        else:
            self._log.debug(
                "hotkey.clipboard_registered",
                "剪贴板热键注册成功",
                hotkey=hotkey,
                hotkeyId=getattr(self._clipboard_mgr, "hotkey_id", 0),
                nativeRegistered=getattr(self._clipboard_mgr, "native_registered", None),
                fallbackRegistered=getattr(self._clipboard_mgr, "fallback_registered", None),
                elapsedMs=int((perf_counter() - started_at) * 1000),
            )

    def refresh_plugin_hotkeys(self, manifests: list[PluginManifest]) -> None:
        started_at = perf_counter()
        self._clear_plugin_hotkeys()
        self._register_plugins(manifests)
        self._log.debug(
            "hotkey.plugin_refresh_complete",
            "插件热键刷新完成",
            manifestCount=len(manifests),
            managerCount=len(self._plugin_managers),
            filterCount=len(self._plugin_filters),
            elapsedMs=int((perf_counter() - started_at) * 1000),
        )

    def unregister_all(self) -> None:
        self._launcher_mgr.unregister()
        self._clipboard_mgr.unregister()
        for mgr in self._plugin_managers:
            mgr.unregister()

    def root_filters(self) -> list[object]:
        filters: list[object] = []
        hotkey_filter = self._platform.hotkey_factory.install_filter(self._qt_app, self._launcher_mgr)
        if hotkey_filter is not None:
            filters.append(hotkey_filter)
        clipboard_filter = self._platform.hotkey_factory.install_filter(self._qt_app, self._clipboard_mgr)
        if clipboard_filter is not None:
            filters.append(clipboard_filter)
        return filters

    def plugin_filters(self) -> list[object]:
        return list(self._plugin_filters)

    def _clear_plugin_hotkeys(self) -> None:
        for mgr in self._plugin_managers:
            mgr.unregister()
        self._plugin_managers.clear()
        self._plugin_filters.clear()

    def _register_plugins(self, manifests: list[PluginManifest]) -> None:
        index = 10
        for manifest in manifests:
            for command in manifest.commands or [manifest.primary_command]:
                hotkey = command.hotkey.strip()
                if not hotkey:
                    continue
                mgr = self._platform.hotkey_factory.create(
                    parent=self._qt_app,
                    hotkey=hotkey,
                    hotkey_id=index,
                )
                if self._hwnd:
                    set_hwnd = getattr(mgr, "set_hwnd", None)
                    if callable(set_hwnd):
                        set_hwnd(self._hwnd)
                if self._on_plugin_launched is not None:
                    mgr.hotkeyPressed.connect(
                        lambda pid=manifest.id, cid=command.id, data=command.payload: self._on_plugin_launched(
                            pid, cid, "", data
                        )
                    )
                if mgr.register():
                    self._plugin_managers.append(mgr)
                    self._log.debug(
                        "hotkey.plugin_registered",
                        "插件热键注册成功",
                        hotkey=hotkey,
                        pluginId=manifest.id,
                        commandId=command.id,
                        hotkeyId=getattr(mgr, "hotkey_id", 0),
                    )
                    filter_item = self._platform.hotkey_factory.install_filter(self._qt_app, mgr)
                    if filter_item is not None:
                        self._plugin_filters.append(filter_item)
                else:
                    self._log.warning(
                        "hotkey.plugin_register_failed",
                        "插件热键注册失败",
                        hotkey=hotkey,
                        pluginId=manifest.id,
                        errorCode=getattr(mgr, "last_error", 0),
                    )
                index += 1

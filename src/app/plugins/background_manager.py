from __future__ import annotations

from collections.abc import Iterable
from threading import Lock

from app.logging import get_logger
from app.plugins.manifest import PluginManifest
from app.plugins.plugin_manager import PluginManager
from app.plugins.runtime import PluginContext


class BackgroundManager:
    """Starts and stops resident background plugin runtimes."""

    def __init__(
        self,
        manifests: Iterable[PluginManifest],
        plugin_manager: PluginManager,
        plugin_context: PluginContext,
    ) -> None:
        self._manifests = [item for item in manifests if item.activation == "background"]
        self._plugin_manager = plugin_manager
        self._plugin_context = plugin_context
        self._running_plugin_ids: set[str] = set()
        self._started = False
        self._lock = Lock()
        self._log = get_logger("app.plugins.background_manager")

    def start_all(self) -> None:
        self._started = True
        for manifest in self._manifests:
            self._start_one(manifest, self._plugin_context)

    def replace_manifests(self, manifests: Iterable[PluginManifest]) -> None:
        self._manifests = [item for item in manifests if item.activation == "background"]

    def refresh_manifests(self, manifests: Iterable[PluginManifest]) -> None:
        should_run = self._started
        self.stop_removed(manifests)
        self.replace_manifests(manifests)
        if should_run:
            self.start_all()

    def stop_removed(self, manifests: Iterable[PluginManifest]) -> None:
        valid_ids = {item.id for item in manifests if item.activation == "background"}
        with self._lock:
            removed = [plugin_id for plugin_id in self._running_plugin_ids if plugin_id not in valid_ids]
        for plugin_id in removed:
            self._stop_one(plugin_id)

    def _start_one(self, manifest: PluginManifest, context: PluginContext) -> None:
        with self._lock:
            if manifest.id in self._running_plugin_ids:
                return
        try:
            runtime = self._plugin_manager.ensure_runtime(manifest.id)
            if runtime is None:
                return
            start = getattr(runtime, "on_background_start", None)
            if callable(start):
                old_platform = context.platform
                old_service_platform = context.services.platform
                if old_platform is not None and hasattr(old_platform, "for_plugin"):
                    scoped_platform = old_platform.for_plugin(manifest.id)
                    context.platform = scoped_platform
                    context.services.platform = scoped_platform
                try:
                    start(context)
                finally:
                    context.platform = old_platform
                    context.services.platform = old_service_platform
            with self._lock:
                self._running_plugin_ids.add(manifest.id)
            self._log.debug("plugin.background.start", "后台插件启动", pluginId=manifest.id)
        except Exception as exc:
            self._log.warning("plugin.background.start_failed", "后台插件启动失败", pluginId=manifest.id, error=str(exc))

    def stop_all(self) -> None:
        with self._lock:
            plugin_ids = list(self._running_plugin_ids)
        for plugin_id in plugin_ids:
            self._stop_one(plugin_id)
        if plugin_ids:
            self._log.debug("plugin.background.stop_all", "停止后台插件", count=len(plugin_ids))
        self._started = False

    def _stop_one(self, plugin_id: str) -> None:
        try:
            runtime = self._plugin_manager.get_loaded_runtime(plugin_id)
            if runtime is not None:
                stop = getattr(runtime, "on_background_stop", None)
                if callable(stop):
                    try:
                        stop()
                    except Exception as exc:
                        self._log.warning("plugin.background.stop_failed", "后台插件停止失败", pluginId=plugin_id, error=str(exc))
        finally:
            with self._lock:
                self._running_plugin_ids.discard(plugin_id)

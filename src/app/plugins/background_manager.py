from __future__ import annotations

from collections.abc import Iterable

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

    def start_all(self) -> None:
        for manifest in self._manifests:
            try:
                runtime = self._plugin_manager.ensure_runtime(manifest.id)
                if runtime is None:
                    continue
                start = getattr(runtime, "on_background_start", None)
                if callable(start):
                    old_platform = self._plugin_context.platform
                    old_service_platform = self._plugin_context.services.get("platform")
                    if old_platform is not None and hasattr(old_platform, "for_plugin"):
                        scoped_platform = old_platform.for_plugin(manifest.id)
                        self._plugin_context.platform = scoped_platform
                        self._plugin_context.services["platform"] = scoped_platform
                    try:
                        start(self._plugin_context)
                    finally:
                        self._plugin_context.platform = old_platform
                        if old_service_platform is not None:
                            self._plugin_context.services["platform"] = old_service_platform
                self._running_plugin_ids.add(manifest.id)
            except Exception as exc:
                print(f"[WARN] 后台插件启动失败: {manifest.id} - {exc}")

    def stop_all(self) -> None:
        for plugin_id in list(self._running_plugin_ids):
            runtime = self._plugin_manager.get_loaded_runtime(plugin_id)
            if runtime is not None:
                stop = getattr(runtime, "on_background_stop", None)
                if callable(stop):
                    try:
                        stop()
                    except Exception as exc:
                        print(f"[WARN] 后台插件停止失败: {plugin_id} - {exc}")
            self._running_plugin_ids.discard(plugin_id)

from __future__ import annotations

from app.commands.dynamic_command_registry import DynamicCommand, DynamicCommandRegistry
from app.plugins.manifest import LaunchMode

from .models import PlatformResult


class PlatformCommandApiFactory:
    def __init__(self, registry: DynamicCommandRegistry | None) -> None:
        self._registry = registry

    def for_plugin(self, plugin_id: str) -> "PluginCommandApi":
        return PluginCommandApi(self._registry, plugin_id)

    def set_registry(self, registry: DynamicCommandRegistry | None) -> None:
        self._registry = registry


class PluginCommandApi:
    def __init__(self, registry: DynamicCommandRegistry | None, plugin_id: str) -> None:
        self._registry = registry
        self._plugin_id = plugin_id

    def register(
        self,
        command_id: str,
        *,
        title: str,
        subtitle: str = "",
        icon: str = "",
        keywords: list[str] | None = None,
        prefixes: list[str] | None = None,
        launch_mode: LaunchMode = "none",
        payload: dict | None = None,
        order: int = 500,
    ) -> PlatformResult:
        if self._registry is None:
            return PlatformResult(False, "动态命令注册器不可用", "unsupported")
        if not self._plugin_id:
            return PlatformResult(False, "缺少插件标识", "invalid")
        normalized_id = str(command_id).strip()
        if not normalized_id:
            return PlatformResult(False, "命令 ID 不能为空", "invalid")
        self._registry.register(
            DynamicCommand(
                plugin_id=self._plugin_id,
                command_id=normalized_id,
                title=title,
                subtitle=subtitle,
                icon=icon,
                keywords=list(keywords or []),
                prefixes=list(prefixes or []),
                launch_mode=launch_mode,
                payload=dict(payload or {}),
                order=order,
            )
        )
        return PlatformResult(True, data={"pluginId": self._plugin_id, "commandId": normalized_id})

    def unregister(self, command_id: str) -> PlatformResult:
        if self._registry is None:
            return PlatformResult(False, "动态命令注册器不可用", "unsupported")
        normalized_id = str(command_id).strip()
        if not normalized_id:
            return PlatformResult(False, "命令 ID 不能为空", "invalid")
        self._registry.unregister(self._plugin_id, normalized_id)
        return PlatformResult(True, data={"pluginId": self._plugin_id, "commandId": normalized_id})

    def unregister_all(self) -> PlatformResult:
        if self._registry is None:
            return PlatformResult(False, "动态命令注册器不可用", "unsupported")
        self._registry.unregister_plugin(self._plugin_id)
        return PlatformResult(True, data={"pluginId": self._plugin_id})

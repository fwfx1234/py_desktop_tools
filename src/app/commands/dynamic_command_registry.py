from __future__ import annotations

from dataclasses import dataclass, field

from app.plugins.manifest import LaunchMode


@dataclass(frozen=True, slots=True)
class DynamicCommand:
    """A command contributed by a plugin at runtime."""

    plugin_id: str
    command_id: str
    title: str
    subtitle: str = ""
    icon: str = ""
    keywords: list[str] = field(default_factory=list)
    prefixes: list[str] = field(default_factory=list)
    matchers: list[object] = field(default_factory=list)
    launch_mode: LaunchMode = "none"
    payload: dict = field(default_factory=dict)
    order: int = 500


class DynamicCommandRegistry:
    """In-memory registry for runtime plugin commands."""

    def __init__(self) -> None:
        self._commands: dict[tuple[str, str], DynamicCommand] = {}

    def register(self, command: DynamicCommand) -> None:
        self._commands[(command.plugin_id, command.command_id)] = command

    def unregister(self, plugin_id: str, command_id: str) -> None:
        self._commands.pop((plugin_id, command_id), None)

    def unregister_plugin(self, plugin_id: str) -> None:
        for key in list(self._commands):
            if key[0] == plugin_id:
                self._commands.pop(key, None)

    def all(self) -> list[DynamicCommand]:
        return list(self._commands.values())

from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import replace
from pathlib import Path
from typing import Literal


PluginActivation = Literal["lazy", "background"]
LaunchMode = Literal["none", "list", "inline_view", "window"]
MatcherSource = Literal["input", "clipboard"]


@dataclass(frozen=True, slots=True)
class ContextMatcher:
    """Declarative context recommendation rule for a command."""

    source: MatcherSource
    kind: str
    boost: int = 0
    pattern: str = ""


@dataclass(frozen=True, slots=True)
class CommandContribution:
    """Static command declared by a plugin manifest."""

    id: str
    title: str
    subtitle: str = ""
    icon: str = ""
    keywords: list[str] = field(default_factory=list)
    prefixes: list[str] = field(default_factory=list)
    matchers: list[ContextMatcher] = field(default_factory=list)
    launch_mode: LaunchMode = "inline_view"
    input_mode: Literal["global", "plugin"] = "plugin"
    hotkey: str = ""
    payload: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """Lightweight plugin metadata loaded at app startup."""

    id: str
    name: str
    version: str
    description: str
    icon: str
    entrypoint: str
    qml_page: str
    context_property: str = ""
    category: str = "tool"
    order: int = 99
    activation: PluginActivation = "lazy"
    window_options: dict = field(default_factory=dict)
    commands: list[CommandContribution] = field(default_factory=list)
    package_dir: Path | None = None

    @property
    def primary_command(self) -> CommandContribution:
        if self.commands:
            return self.commands[0]
        return CommandContribution(
            id=f"{self.id}.open",
            title=self.name,
            subtitle=self.description,
            icon=self.icon,
        )

    def with_order(self, order: int) -> PluginManifest:
        return replace(self, order=order)

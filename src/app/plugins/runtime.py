from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

from PySide6.QtCore import QObject

from app.plugins.manifest import LaunchMode, PluginManifest


@dataclass(slots=True)
class PluginContext:
    """Services a plugin runtime can use without importing the app kernel."""

    command_index: object | None = None
    dynamic_commands: object | None = None
    platform: object | None = None
    services: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class PluginAction:
    """Information passed when a launcher command enters a plugin."""

    manifest: PluginManifest
    command_id: str
    input_text: str = ""
    payload: dict = field(default_factory=dict)


class PluginSession(Protocol):
    manifest: PluginManifest
    launch_mode: LaunchMode

    def create_qml_context(self) -> dict[str, QObject]:
        ...

    def qml_page(self) -> str:
        ...

    def list_model(self) -> list[dict]:
        ...

    def on_input_changed(self, text: str) -> list[dict]:
        ...

    def on_list_item_selected(self, item_id: str) -> None:
        ...

    def on_list_item_action(self, item_id: str, action_id: str) -> list[dict]:
        ...

    def reactivate(self, action: PluginAction) -> None:
        ...

    def close(self) -> None:
        ...


class PluginRuntime(Protocol):
    def on_enter(self, ctx: PluginContext, action: PluginAction) -> PluginSession:
        ...

    def on_exit(self) -> None:
        ...


class QmlPluginSession:
    """A session that exposes one optional QObject ViewModel to one QML page."""

    def __init__(
        self,
        manifest: PluginManifest,
        launch_mode: LaunchMode,
        view_model: QObject | None = None,
    ) -> None:
        self.manifest = manifest
        self.launch_mode = launch_mode
        self._view_model = view_model

    def create_qml_context(self) -> dict[str, QObject]:
        if self._view_model is None or not self.manifest.context_property:
            return {}
        return {self.manifest.context_property: self._view_model}

    def qml_page(self) -> str:
        return self.manifest.qml_page

    def list_model(self) -> list[dict]:
        return []

    def on_input_changed(self, text: str) -> list[dict]:
        del text
        return []

    def on_list_item_selected(self, item_id: str) -> None:
        del item_id
        return

    def on_list_item_action(self, item_id: str, action_id: str) -> list[dict]:
        del item_id, action_id
        return []

    def reactivate(self, action: PluginAction) -> None:
        """Best-effort wake-up hook for retained sessions.

        The default implementation intentionally does very little. It updates the
        session from fresh launcher input by forwarding the text through the same
        path used while the plugin is already active.
        """

        if action.input_text:
            self.on_input_changed(action.input_text)

    def close(self) -> None:
        if self._view_model is not None:
            dispose = getattr(self._view_model, "dispose", None)
            if callable(dispose):
                try:
                    dispose()
                except Exception as exc:
                    print(f"[WARN] ViewModel dispose 失败: {exc}")
            self._view_model.deleteLater()
            self._view_model = None


class NoopPluginSession:
    """A session for commands that execute immediately and show no UI."""

    def __init__(self, manifest: PluginManifest) -> None:
        self.manifest = manifest
        self.launch_mode = "none"

    def create_qml_context(self) -> dict[str, QObject]:
        return {}

    def qml_page(self) -> str:
        return ""

    def list_model(self) -> list[dict]:
        return []

    def on_input_changed(self, text: str) -> list[dict]:
        del text
        return []

    def on_list_item_selected(self, item_id: str) -> None:
        del item_id
        return

    def on_list_item_action(self, item_id: str, action_id: str) -> list[dict]:
        del item_id, action_id
        return []

    def reactivate(self, action: PluginAction) -> None:
        del action
        return

    def close(self) -> None:
        return


class SimpleQmlRuntime:
    """Runtime helper for existing QML + ViewModel feature modules."""

    def __init__(self, view_model_factory: Callable[[PluginContext], QObject | None]) -> None:
        self._view_model_factory = view_model_factory

    def on_enter(self, ctx: PluginContext, action: PluginAction) -> QmlPluginSession:
        return QmlPluginSession(
            manifest=action.manifest,
            launch_mode=action.manifest.primary_command.launch_mode,
            view_model=self._view_model_factory(ctx),
        )

    def on_exit(self) -> None:
        return

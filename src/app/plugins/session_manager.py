from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Literal

from PySide6.QtCore import QObject, QTimer
from PySide6.QtQml import QQmlContext

from app.plugins.manifest import LaunchMode, PluginManifest
from app.plugins.plugin_manager import PluginManager
from app.plugins.runtime import (
    NoopPluginSession,
    PluginAction,
    PluginContext,
    PluginSession,
    QmlPluginSession,
)


SessionState = Literal[
    "active_inline",
    "active_list",
    "active_window",
    "retained_inline",
    "retained_list",
    "retained_window",
]

RetentionExpiredCallback = Callable[[str, SessionState], None]


def _retention_interval_ms() -> int:
    """Read the retention interval from env for debugging, otherwise use 5 minutes."""

    raw = os.getenv("PY_DESKTOP_PLUGIN_RETENTION_MS", "").strip()
    if not raw:
        return 300_000
    try:
        value = int(raw)
    except ValueError:
        return 300_000
    return max(1_000, value)


@dataclass(slots=True)
class ManagedPluginSession:
    """In-memory record for a plugin session and its retention state.

    The key idea is that closing the visible UI should not immediately destroy
    the Python session. We keep the session, its QML context bindings, and a
    single-shot timer here so the UI can be revived for a short window.
    """

    plugin_id: str
    session: PluginSession
    state: SessionState
    context_names: set[str] = field(default_factory=set)
    retain_timer: QTimer | None = None
    last_action: PluginAction | None = None


class PluginSessionManager:
    """Own active and retained plugin sessions plus their QML context objects."""

    def __init__(
        self,
        qml_context: QQmlContext,
        plugin_manager: PluginManager,
        plugin_context: PluginContext,
        *,
        on_retention_expired: RetentionExpiredCallback | None = None,
    ) -> None:
        self._qml_context = qml_context
        self._plugin_manager = plugin_manager
        self._plugin_context = plugin_context
        self._on_retention_expired = on_retention_expired
        self._retention_ms = _retention_interval_ms()
        self._sessions: dict[str, ManagedPluginSession] = {}

    def get_manifest(self, plugin_id: str) -> PluginManifest | None:
        return self._plugin_manager.get_manifest(plugin_id)

    def get_session(self, plugin_id: str) -> PluginSession | None:
        record = self._sessions.get(plugin_id)
        return record.session if record is not None else None

    def get_session_state(self, plugin_id: str) -> SessionState | None:
        record = self._sessions.get(plugin_id)
        return record.state if record is not None else None

    def has_session(self, plugin_id: str) -> bool:
        return plugin_id in self._sessions

    def can_reuse_plugin(
        self,
        plugin_id: str,
        *,
        command_id: str = "",
        input_text: str = "",
        payload: dict | None = None,
    ) -> bool:
        record = self._sessions.get(plugin_id)
        if record is None:
            return False
        action = self._build_action(
            plugin_id,
            command_id=command_id,
            input_text=input_text,
            payload=payload,
        )
        if action is None:
            return False
        return self._can_reuse_session(record, action)

    def open_plugin(
        self,
        plugin_id: str,
        *,
        command_id: str = "",
        input_text: str = "",
        payload: dict | None = None,
        preferred_host: Literal["inline", "list", "window"] | None = None,
    ) -> PluginSession | None:
        """Open a plugin, reusing a retained session when it is safe to do so.

        The manager preserves sessions for a short period after UI close. When a
        plugin is launched again during that window, we prefer reusing the old
        session so ViewModel state and transient service state remain intact.
        """

        record = self._sessions.get(plugin_id)
        action = self._build_action(
            plugin_id,
            command_id=command_id,
            input_text=input_text,
            payload=payload,
        )
        if action is None:
            return None

        if record is not None:
            if self._can_reuse_session(record, action):
                self._stop_retention_timer(record)
                record.last_action = action
                self._mark_session_active(record, preferred_host)
                self._reactivate_session(record, action)
                return record.session
            self.unload_plugin(plugin_id)

        session = self._create_session(plugin_id, action)
        if session is None:
            return None
        context_names = self._bind_session_context(session)
        record = ManagedPluginSession(
            plugin_id=plugin_id,
            session=session,
            state=self._active_state_for(session.launch_mode, preferred_host),
            context_names=context_names,
            last_action=action,
        )
        self._sessions[plugin_id] = record
        return session

    def plugin_launch_mode(self, plugin_id: str) -> LaunchMode | None:
        record = self._sessions.get(plugin_id)
        if record is not None:
            return record.session.launch_mode
        manifest = self.get_manifest(plugin_id)
        if manifest is None:
            return None
        return manifest.primary_command.launch_mode

    def list_items(self, plugin_id: str) -> list[dict]:
        record = self._sessions.get(plugin_id)
        return record.session.list_model() if record is not None else []

    def update_plugin_input(self, plugin_id: str, text: str) -> list[dict]:
        record = self._sessions.get(plugin_id)
        if record is None:
            return []
        return record.session.on_input_changed(text)

    def activate_list_item(self, plugin_id: str, item_id: str) -> list[dict]:
        record = self._sessions.get(plugin_id)
        if record is None:
            return []
        record.session.on_list_item_selected(item_id)
        return record.session.list_model()

    def activate_list_item_action(
        self,
        plugin_id: str,
        item_id: str,
        action_id: str,
    ) -> list[dict]:
        record = self._sessions.get(plugin_id)
        if record is None:
            return []
        items = record.session.on_list_item_action(item_id, action_id)
        return items if items is not None else record.session.list_model()

    def suspend_plugin(
        self,
        plugin_id: str,
        host: Literal["inline", "list", "window"],
    ) -> None:
        """Move a live session into retained state without disposing it.

        This is the key behavior change for the feature. The session and runtime
        stay alive, so re-opening the plugin within the retention window can pick
        up where the user left off.
        """

        record = self._sessions.get(plugin_id)
        if record is None:
            return
        record.state = self._retained_state_for(record.session.launch_mode, host)
        timer = record.retain_timer
        if timer is None:
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(
                lambda pid=plugin_id: self._handle_retention_timeout(pid)
            )
            record.retain_timer = timer
        timer.start(self._retention_ms)

    def unload_plugin(self, plugin_id: str) -> None:
        """Immediately destroy a session and release its runtime."""

        record = self._sessions.pop(plugin_id, None)
        manifest = self.get_manifest(plugin_id)
        if record is not None:
            self._stop_retention_timer(record, discard=True)
            for name in record.context_names:
                self._qml_context.setContextProperty(name, None)
            try:
                record.session.close()
            except Exception as exc:
                print(f"[WARN] plugin session close failed: {plugin_id} - {exc}")
        elif manifest is not None and manifest.context_property:
            self._qml_context.setContextProperty(manifest.context_property, None)
        self._plugin_manager.close_runtime(plugin_id)

    def close_plugin(self, plugin_id: str) -> None:
        """Backward-compatible alias for full unload.

        Older call sites still use close_plugin(). Keeping the method avoids a
        large, brittle mechanical rename while we migrate call sites gradually.
        """

        self.unload_plugin(plugin_id)

    def close_all(self) -> None:
        for plugin_id in list(self._sessions):
            self.unload_plugin(plugin_id)

    def _build_action(
        self,
        plugin_id: str,
        *,
        command_id: str,
        input_text: str,
        payload: dict | None,
    ) -> PluginAction | None:
        manifest = self.get_manifest(plugin_id)
        if manifest is None:
            return None
        return PluginAction(
            manifest=manifest,
            command_id=command_id or manifest.primary_command.id,
            input_text=input_text,
            payload=dict(payload or {}),
        )

    def _create_session(self, plugin_id: str, action: PluginAction) -> PluginSession | None:
        """Create a brand-new session under a plugin-scoped platform context."""

        session = None
        old_platform = self._plugin_context.platform
        old_service_platform = self._plugin_context.services.get("platform")
        if old_platform is not None and hasattr(old_platform, "for_plugin"):
            scoped_platform = old_platform.for_plugin(plugin_id)
            self._plugin_context.platform = scoped_platform
            self._plugin_context.services["platform"] = scoped_platform
        try:
            session = self._plugin_manager.open_session(
                plugin_id,
                self._plugin_context,
                command_id=action.command_id,
                input_text=action.input_text,
                payload=action.payload,
            )
        finally:
            self._plugin_context.platform = old_platform
            if old_service_platform is not None:
                self._plugin_context.services["platform"] = old_service_platform
        return session

    def _bind_session_context(self, session: PluginSession) -> set[str]:
        """Expose a session's QObject bindings to QML and remember their names."""

        context_names: set[str] = set()
        try:
            for name, obj in session.create_qml_context().items():
                self._qml_context.setContextProperty(name, obj)
                context_names.add(name)
        except Exception:
            for name in context_names:
                self._qml_context.setContextProperty(name, None)
            try:
                session.close()
            finally:
                self._plugin_manager.close_runtime(session.manifest.id)
            raise
        return context_names

    def _can_reuse_session(self, record: ManagedPluginSession, action: PluginAction) -> bool:
        """Decide whether an existing session can safely serve a new launch.

        We always reuse when the new launch is effectively a wake-up. When the
        user provides fresh input or payload we try an explicit reactivate hook;
        otherwise we rebuild to avoid stale state swallowing new intent.
        """

        previous = record.last_action
        if previous is None:
            return True
        previous_payload = self._normalized_payload(previous.payload)
        current_payload = self._normalized_payload(action.payload)
        if (
            previous.command_id == action.command_id
            and previous.input_text == action.input_text
            and previous_payload == current_payload
        ):
            return True
        if (
            previous.command_id == action.command_id
            and not current_payload
            and not previous_payload
        ):
            return True
        return self._has_custom_reactivate(record.session)

    def _reactivate_session(self, record: ManagedPluginSession, action: PluginAction) -> None:
        """Apply a new launch action to a reused session when the session supports it."""

        reactivate = getattr(record.session, "reactivate", None)
        if callable(reactivate):
            reactivate(action)

    @staticmethod
    def _normalized_payload(payload: dict) -> dict:
        """Strip launcher-only transport flags before comparing user intent."""

        return {
            key: value
            for key, value in dict(payload or {}).items()
            if key not in {"clearLauncherInputOnEnter", "openInWindow"}
        }

    @staticmethod
    def _has_custom_reactivate(session: PluginSession) -> bool:
        """Only reuse for payload/command changes when a session opted in explicitly."""

        reactivate = getattr(session, "reactivate", None)
        if not callable(reactivate):
            return False
        func = getattr(reactivate, "__func__", reactivate)
        return func not in {
            QmlPluginSession.reactivate,
            NoopPluginSession.reactivate,
        }

    def _mark_session_active(
        self,
        record: ManagedPluginSession,
        preferred_host: Literal["inline", "list", "window"] | None,
    ) -> None:
        if preferred_host == "window":
            record.state = "active_window"
            return
        if preferred_host == "list":
            record.state = "active_list"
            return
        if preferred_host == "inline":
            record.state = "active_inline"
            return
        if record.state.endswith("window"):
            record.state = "active_window"
            return
        if record.state.endswith("list"):
            record.state = "active_list"
            return
        record.state = self._active_state_for(record.session.launch_mode, None)

    def _active_state_for(
        self,
        launch_mode: LaunchMode,
        preferred_host: Literal["inline", "list", "window"] | None,
    ) -> SessionState:
        if preferred_host == "window":
            return "active_window"
        if preferred_host == "list" or launch_mode == "list":
            return "active_list"
        return "active_inline" if launch_mode == "inline_view" else "active_window"

    def _retained_state_for(
        self,
        launch_mode: LaunchMode,
        host: Literal["inline", "list", "window"],
    ) -> SessionState:
        if host == "window":
            return "retained_window"
        if host == "list" or launch_mode == "list":
            return "retained_list"
        return "retained_inline"

    def _stop_retention_timer(
        self,
        record: ManagedPluginSession,
        *,
        discard: bool = False,
    ) -> None:
        timer = record.retain_timer
        if timer is None:
            return
        timer.stop()
        if discard:
            timer.deleteLater()
            record.retain_timer = None

    def _handle_retention_timeout(self, plugin_id: str) -> None:
        record = self._sessions.get(plugin_id)
        if record is None:
            return
        expired_state = record.state
        if self._on_retention_expired is not None:
            self._on_retention_expired(plugin_id, expired_state)
            return
        self.unload_plugin(plugin_id)

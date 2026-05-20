from __future__ import annotations

from threading import RLock

from app.plugins.manifest import LaunchMode

from .executor import QuickLaunchExecutor
from .repository import QuickLaunchAction, QuickLaunchRepository


class QuickLaunchRegistrar:
    """Keeps the dynamic command registry in sync with quick-launch actions.

    Uses an action_id -> command_id mapping to do incremental
    register / unregister / update on every change.
    """

    def __init__(
        self,
        repository: QuickLaunchRepository,
        executor: QuickLaunchExecutor,
        commands_api: object,
    ) -> None:
        self._repository = repository
        self._executor = executor
        self._commands_api = commands_api
        self._lock = RLock()
        self._registered: dict[int, str] = {}

    def sync_all(self) -> None:
        """Reload all enabled actions and reconcile registrations."""
        actions = {
            action.id: action
            for action in self._repository.list_actions(enabled=True)
        }
        with self._lock:
            previous_ids = set(self._registered.keys())
            current_ids = set(actions.keys())
            for action_id in previous_ids - current_ids:
                self._unregister_locked(action_id)
            for action_id, action in actions.items():
                self._register_locked(action)

    def sync_action(self, action_id: int) -> None:
        """Reconcile registration for a single action after create/update/delete."""
        action = self._repository.get_action(action_id)
        with self._lock:
            if action is None or not action.enabled:
                self._unregister_locked(action_id)
                return
            self._register_locked(action)

    def unregister_all(self) -> None:
        with self._lock:
            self._registered.clear()
        try:
            self._commands_api.unregister_all()
        except Exception:
            pass

    # ----- internal -----

    def _register_locked(self, action: QuickLaunchAction) -> None:
        command_id = self._command_id_for(action.id)
        needs_form = bool(self._executor.required_parameters(action))
        launch_mode: LaunchMode = "window" if needs_form else "none"
        subtitle = action.description or self._default_subtitle(action)
        icon = action.icon or "qta:fa5s.bolt"
        keywords = list(action.keywords or [])
        if action.name and action.name not in keywords:
            keywords.append(action.name)
        self._commands_api.register(
            command_id,
            title=action.name or "未命名动作",
            subtitle=subtitle,
            icon=icon,
            keywords=keywords,
            prefixes=list(action.prefixes or []),
            launch_mode=launch_mode,
            payload={
                "actionId": action.id,
                "mode": "form" if needs_form else "run",
            },
            order=500 + int(action.sort_order or 0),
        )
        self._registered[action.id] = command_id

    def _unregister_locked(self, action_id: int) -> None:
        command_id = self._registered.pop(action_id, None)
        if command_id:
            try:
                self._commands_api.unregister(command_id)
            except Exception:
                pass

    @staticmethod
    def _command_id_for(action_id: int) -> str:
        return f"action.{int(action_id)}"

    @staticmethod
    def _default_subtitle(action: QuickLaunchAction) -> str:
        if action.kind == "script":
            prefix = action.script_type if action.script_type else ""
            target = action.path or ""
            return f"{prefix}: {target}" if prefix else target
        if action.kind == "open_path":
            return action.path
        if action.kind == "open_url":
            return action.url
        return ""

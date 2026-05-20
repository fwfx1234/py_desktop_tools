from __future__ import annotations

from app.plugins.manifest import PluginManifest
from app.plugins.runtime import NoopPluginSession, PluginAction, PluginContext, QmlPluginSession

from .executor import QuickLaunchExecutor
from .registrar import QuickLaunchRegistrar
from .repository import QuickLaunchRepository


def _log():
    from app.logging import get_logger

    return get_logger("features.quick_launch.runtime")


class QuickLaunchRuntime:
    def __init__(self) -> None:
        self._repository: QuickLaunchRepository | None = None
        self._executor: QuickLaunchExecutor | None = None
        self._registrar: QuickLaunchRegistrar | None = None
        self._scoped_platform: object | None = None

    def on_background_start(self, ctx: PluginContext) -> None:
        if self._repository is not None:
            return
        platform = ctx.platform or ctx.services.platform
        if platform is None:
            raise RuntimeError("Platform API is unavailable")
        self._scoped_platform = platform
        database = platform.storage.database("quick_launch.db", check_same_thread=False)
        self._repository = QuickLaunchRepository(database)
        self._executor = QuickLaunchExecutor(self._repository, platform)
        self._registrar = QuickLaunchRegistrar(
            self._repository,
            self._executor,
            platform.commands,
        )
        self._registrar.sync_all()
        _log().debug(
            "quick_launch.background.start",
            "快速启动后台启动",
            actionCount=len(self._registrar._registered),
        )

    def on_enter(self, ctx: PluginContext, action: PluginAction):
        if self._repository is None:
            self.on_background_start(ctx)
        assert self._repository is not None and self._executor is not None and self._registrar is not None

        payload = dict(action.payload or {})
        action_id = self._coerce_int(payload.get("actionId"))
        mode = str(payload.get("mode") or "")

        if action_id is not None and mode == "run":
            self._run_action_silently(action_id)
            return NoopPluginSession(action.manifest)

        from .view_model import QuickLaunchViewModel

        initial_action_id = action_id if action_id is not None else 0
        initial_mode = "form" if mode == "form" else "manage"
        view_model = QuickLaunchViewModel(
            self._repository,
            self._executor,
            self._registrar,
            initial_action_id=initial_action_id,
            initial_mode=initial_mode,
            platform=self._scoped_platform,
        )
        return QmlPluginSession(
            manifest=action.manifest,
            launch_mode="window",
            view_model=view_model,
        )

    def on_background_stop(self) -> None:
        if self._registrar is not None:
            self._registrar.unregister_all()
        self._registrar = None
        self._executor = None
        self._repository = None
        self._scoped_platform = None

    def on_exit(self) -> None:
        return

    def _run_action_silently(self, action_id: int) -> None:
        assert self._repository is not None and self._executor is not None
        action = self._repository.get_action(action_id)
        if action is None:
            _log().warning("quick_launch.run.missing", "动作不存在", actionId=action_id)
            return
        result = self._executor.execute(action)
        if not result.ok:
            _log().warning(
                "quick_launch.run.failed",
                "动作执行失败",
                actionId=action_id,
                status=result.status,
                message=result.message,
            )

    @staticmethod
    def _coerce_int(value: object) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


def create_runtime() -> QuickLaunchRuntime:
    return QuickLaunchRuntime()

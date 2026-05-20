from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from .executor import QuickLaunchExecutor
from .registrar import QuickLaunchRegistrar
from .repository import QuickLaunchRepository


def _log():
    from app.logging import get_logger

    return get_logger("features.quick_launch.view_model")


class QuickLaunchViewModel(QObject):
    actionsChanged = Signal()
    runsChanged = Signal()
    pendingActionChanged = Signal()
    pendingParametersChanged = Signal()
    initialModeChanged = Signal()
    feedbackMessageChanged = Signal()
    popupResult = Signal("QVariantMap")
    searchQueryChanged = Signal()

    def __init__(
        self,
        repository: QuickLaunchRepository,
        executor: QuickLaunchExecutor,
        registrar: QuickLaunchRegistrar,
        *,
        initial_action_id: int = 0,
        initial_mode: str = "manage",
        platform: object | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._executor = executor
        self._registrar = registrar
        self._platform = platform
        self._actions: list[dict] = []
        self._runs: list[dict] = []
        self._search_query = ""
        self._pending_action_id: int = 0
        self._pending_parameters: list[dict] = []
        self._initial_mode = initial_mode
        self._feedback_message: str = ""
        self._reload_actions()
        self._reload_runs()
        if initial_action_id > 0 and initial_mode == "form":
            self._open_pending(initial_action_id)

    # ----- properties -----

    @Property("QVariantList", notify=actionsChanged)
    def actions(self) -> list[dict]:
        return list(self._actions)

    @Property("QVariantList", notify=runsChanged)
    def runs(self) -> list[dict]:
        return list(self._runs)

    @Property(str, notify=searchQueryChanged)
    def searchQuery(self) -> str:
        return self._search_query

    @Property(int, notify=pendingActionChanged)
    def pendingActionId(self) -> int:
        return self._pending_action_id

    @Property("QVariantList", notify=pendingParametersChanged)
    def pendingParameters(self) -> list[dict]:
        return list(self._pending_parameters)

    @Property(str, notify=initialModeChanged)
    def initialMode(self) -> str:
        return self._initial_mode

    @Property(str, notify=feedbackMessageChanged)
    def feedbackMessage(self) -> str:
        return self._feedback_message

    # ----- search -----

    @Slot(str)
    def setSearchQuery(self, text: str) -> None:
        normalized = (text or "").strip()
        if normalized == self._search_query:
            return
        self._search_query = normalized
        self.searchQueryChanged.emit()
        self._reload_actions()

    # ----- action CRUD -----

    @Slot("QVariantMap", result=int)
    def createAction(self, payload: dict) -> int:
        params = self._normalize_action_payload(payload)
        if not params["name"]:
            self._set_feedback("动作名称不能为空")
            return 0
        action = self._repository.create_action(**params)
        self._reload_actions()
        self._registrar.sync_action(action.id)
        self._set_feedback(f"已创建动作 {action.name}")
        return action.id

    @Slot(int, "QVariantMap", result=bool)
    def updateAction(self, action_id: int, payload: dict) -> bool:
        if action_id <= 0:
            return False
        params = self._normalize_action_payload(payload)
        updated = self._repository.update_action(int(action_id), **params)
        if updated is None:
            return False
        self._reload_actions()
        self._registrar.sync_action(int(action_id))
        self._set_feedback(f"已保存动作 {updated.name}")
        return True

    @Slot(int, result=bool)
    def deleteAction(self, action_id: int) -> bool:
        if action_id <= 0:
            return False
        ok = self._repository.delete_action(int(action_id))
        if not ok:
            return False
        self._registrar.sync_action(int(action_id))
        self._reload_actions()
        self._set_feedback("已删除动作")
        return True

    @Slot(int, bool, result=bool)
    def setActionEnabled(self, action_id: int, enabled: bool) -> bool:
        if action_id <= 0:
            return False
        updated = self._repository.set_action_enabled(int(action_id), bool(enabled))
        if updated is None:
            return False
        self._reload_actions()
        self._registrar.sync_action(int(action_id))
        self._set_feedback("已启用" if enabled else "已停用")
        return True

    @Slot(int, result=bool)
    def duplicateAction(self, action_id: int) -> bool:
        existing = self._repository.get_action(int(action_id))
        if existing is None:
            return False
        cloned = self._repository.create_action(
            name=f"{existing.name} 副本",
            description=existing.description,
            kind=existing.kind,
            script_type=existing.script_type,
            interpreter=existing.interpreter,
            path=existing.path,
            url=existing.url,
            args=existing.args,
            cwd=existing.cwd,
            env=existing.env,
            keywords=existing.keywords,
            prefixes=existing.prefixes,
            icon=existing.icon,
            feedback_mode=existing.feedback_mode,
            timeout_sec=existing.timeout_sec,
            enabled=existing.enabled,
        )
        self._reload_actions()
        self._registrar.sync_action(cloned.id)
        self._set_feedback(f"已复制为 {cloned.name}")
        return True

    @Slot(int, result="QVariantMap")
    def actionDetail(self, action_id: int) -> dict:
        action = self._repository.get_action(int(action_id))
        return action.to_dict() if action else {}

    @Slot(int, result="QVariantList")
    def parametersOf(self, action_id: int) -> list[dict]:
        action = self._repository.get_action(int(action_id))
        if action is None:
            return []
        names = self._executor.required_parameters(action)
        return [{"name": name, "value": ""} for name in names]

    # ----- execution -----

    @Slot(int, result="QVariantMap")
    def runNow(self, action_id: int) -> dict:
        action = self._repository.get_action(int(action_id))
        if action is None:
            return {"ok": False, "status": "error", "message": "动作不存在"}
        params = self._executor.required_parameters(action)
        if params:
            self._open_pending(action_id)
            return {
                "ok": False,
                "status": "needsParameters",
                "message": "请填写参数后再执行",
                "parameters": [{"name": name, "value": ""} for name in params],
            }
        result = self._executor.execute(action)
        self._reload_runs()
        message = result.message or ("执行成功" if result.ok else "执行失败")
        self._set_feedback(message)
        self._maybe_emit_popup(action.id, action.name, result)
        return {"ok": result.ok, "status": result.status, "message": message}

    @Slot(int, "QVariantMap", result="QVariantMap")
    def runWithParameters(self, action_id: int, parameters: dict) -> dict:
        action = self._repository.get_action(int(action_id))
        if action is None:
            return {"ok": False, "status": "error", "message": "动作不存在"}
        normalized = {str(k): "" if v is None else str(v) for k, v in (parameters or {}).items()}
        result = self._executor.execute(action, parameters=normalized)
        self._reload_runs()
        if result.status == "error" and result.missing_parameters:
            message = f"缺少参数: {', '.join(result.missing_parameters)}"
            self._set_feedback(message)
            return {
                "ok": False,
                "status": "needsParameters",
                "message": message,
                "missing": list(result.missing_parameters),
            }
        message = result.message or ("执行成功" if result.ok else "执行失败")
        self._set_feedback(message)
        if result.ok:
            self._clear_pending()
        self._maybe_emit_popup(action.id, action.name, result)
        return {"ok": result.ok, "status": result.status, "message": message}

    @Slot()
    def clearPending(self) -> None:
        self._clear_pending()

    @Slot()
    def refreshRuns(self) -> None:
        self._reload_runs()

    # ----- platform helpers (native file pickers) -----

    @Slot(result=str)
    def pickScriptFile(self) -> str:
        if self._platform is None:
            return ""
        try:
            from app.platform.models import FileDialogFilter, FileDialogOptions

            opts = FileDialogOptions(
                title="选择脚本文件",
                filters=[
                    FileDialogFilter(name="脚本", patterns=["*.sh", "*.zsh", "*.bash", "*.js", "*.mjs", "*.cjs", "*.ts", "*.py", "*"]),
                ],
            )
            path = self._platform.dialogs.open_file(opts)
            return str(path) if path else ""
        except Exception:
            return ""

    @Slot(result=str)
    def pickDirectory(self) -> str:
        if self._platform is None:
            return ""
        try:
            from app.platform.models import FileDialogOptions

            opts = FileDialogOptions(title="选择工作目录")
            path = self._platform.dialogs.open_directory(opts)
            return str(path) if path else ""
        except Exception:
            return ""

    # ----- internals -----

    def _maybe_emit_popup(self, action_id: int, action_name: str, result) -> None:
        if result.feedback_mode != "popup":
            return
        run = result.run
        payload = {
            "actionId": action_id,
            "actionName": action_name,
            "status": result.status,
            "ok": result.ok,
            "exitCode": run.exit_code if run else None,
            "durationMs": run.duration_ms if run else 0,
            "stdout": run.stdout if run else "",
            "stderr": run.stderr if run else "",
            "message": result.message,
        }
        self.popupResult.emit(payload)

    def _normalize_action_payload(self, payload: dict) -> dict[str, Any]:
        payload = dict(payload or {})
        keywords = self._coerce_str_list(payload.get("keywords"))
        prefixes = self._coerce_str_list(payload.get("prefixes"))
        env_raw = payload.get("env") or {}
        env: dict[str, str]
        if isinstance(env_raw, dict):
            env = {str(k): "" if v is None else str(v) for k, v in env_raw.items()}
        else:
            env = {}
        feedback_mode = str(payload.get("feedbackMode") or "notification")
        if feedback_mode not in {"silent", "popup", "notification"}:
            feedback_mode = "notification"
        kind = str(payload.get("kind") or "script")
        if kind not in {"script", "open_path", "open_url"}:
            kind = "script"
        script_type = str(payload.get("scriptType") or "shell")
        if script_type not in {"shell", "node", "python", "other"}:
            script_type = "shell"
        try:
            timeout_sec = int(payload.get("timeoutSec") or 300)
        except (TypeError, ValueError):
            timeout_sec = 300
        return {
            "name": str(payload.get("name") or "").strip(),
            "description": str(payload.get("description") or ""),
            "kind": kind,
            "script_type": script_type,
            "interpreter": str(payload.get("interpreter") or ""),
            "path": str(payload.get("path") or ""),
            "url": str(payload.get("url") or ""),
            "args": str(payload.get("args") or ""),
            "cwd": str(payload.get("cwd") or ""),
            "env": env,
            "keywords": keywords,
            "prefixes": prefixes,
            "icon": str(payload.get("icon") or ""),
            "feedback_mode": feedback_mode,
            "timeout_sec": timeout_sec,
            "enabled": bool(payload.get("enabled", True)),
        }

    @staticmethod
    def _coerce_str_list(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, (list, tuple)):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    def _reload_actions(self) -> None:
        items = self._repository.list_actions()
        query = self._search_query.lower()
        if query:
            filtered: list = []
            for item in items:
                haystack = " ".join([
                    item.name,
                    item.description,
                    item.path,
                    item.url,
                    item.args,
                    " ".join(item.keywords or []),
                    " ".join(item.prefixes or []),
                ]).lower()
                if query in haystack:
                    filtered.append(item)
            items = filtered
        self._actions = [action.to_dict() for action in items]
        self.actionsChanged.emit()

    def _reload_runs(self) -> None:
        runs = self._repository.list_runs(limit=50)
        self._runs = [run.to_dict() for run in runs]
        self.runsChanged.emit()

    def _open_pending(self, action_id: int) -> None:
        action = self._repository.get_action(int(action_id))
        if action is None:
            return
        names = self._executor.required_parameters(action)
        self._pending_action_id = action.id
        self._pending_parameters = [{"name": name, "value": ""} for name in names]
        self.pendingActionChanged.emit()
        self.pendingParametersChanged.emit()

    def _clear_pending(self) -> None:
        if self._pending_action_id == 0 and not self._pending_parameters:
            return
        self._pending_action_id = 0
        self._pending_parameters = []
        self.pendingActionChanged.emit()
        self.pendingParametersChanged.emit()

    def _set_feedback(self, message: str) -> None:
        self._feedback_message = message
        self.feedbackMessageChanged.emit()

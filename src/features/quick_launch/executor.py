from __future__ import annotations

import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter

from .parameters import MissingParameterError, extract_parameters, substitute, substitute_mapping
from .repository import QuickLaunchAction, QuickLaunchRepository, QuickLaunchRun


@dataclass(slots=True)
class ExecutionResult:
    ok: bool
    status: str  # success | failed | timeout | error
    message: str = ""
    run: QuickLaunchRun | None = None
    missing_parameters: list[str] | None = None
    feedback_mode: str = "silent"


SCRIPT_INTERPRETERS: dict[str, list[str]] = {
    "shell": ["/bin/zsh"],
    "node": ["node"],
    "python": ["python3"],
}


class QuickLaunchExecutor:
    """Dispatch actions (script / open_path / open_url) and record results."""

    def __init__(
        self,
        repository: QuickLaunchRepository,
        platform: object,
        *,
        subprocess_run=None,
        notification_runner=None,
    ) -> None:
        self._repository = repository
        self._platform = platform
        self._subprocess_run = subprocess_run or self._default_subprocess_run
        self._notification_runner = notification_runner or self._default_notification_runner

    def required_parameters(self, action: QuickLaunchAction) -> list[str]:
        sources = [action.path, action.url, action.args, action.cwd, action.interpreter]
        sources.extend(action.env.values())
        return [spec.name for spec in extract_parameters(*sources)]

    def execute(
        self,
        action: QuickLaunchAction,
        *,
        parameters: dict[str, str] | None = None,
    ) -> ExecutionResult:
        values = {str(k): "" if v is None else str(v) for k, v in (parameters or {}).items()}
        try:
            if action.kind == "script":
                result = self._execute_script(action, values)
            elif action.kind == "open_path":
                result = self._execute_open_path(action, values)
            elif action.kind == "open_url":
                result = self._execute_open_url(action, values)
            else:
                result = self._record_error(action, f"未知动作类型: {action.kind}")
        except MissingParameterError as exc:
            return ExecutionResult(
                ok=False,
                status="error",
                message=str(exc),
                missing_parameters=list(exc.missing),
                feedback_mode=action.feedback_mode,
            )
        result.feedback_mode = action.feedback_mode
        if action.feedback_mode == "notification":
            self._emit_notification(action, result)
        return result

    # ----- kind handlers -----

    def _execute_script(self, action: QuickLaunchAction, values: dict[str, str]) -> ExecutionResult:
        path = substitute(action.path, values, quote=False).strip()
        if not path:
            return self._record_error(action, "脚本路径为空")
        argv = self._build_script_argv(action, path, values)
        cwd = self._resolve_cwd(action, values)
        env = self._resolve_env(action, values)
        return self._dispatch_capture(action, argv, cwd=cwd, env=env)

    def _execute_open_path(
        self, action: QuickLaunchAction, values: dict[str, str]
    ) -> ExecutionResult:
        path = substitute(action.path, values, quote=False).strip()
        if not path:
            return self._record_error(action, "目标路径为空")
        result = self._platform.open_path(path)
        return self._record_platform_result(action, result, "open_path")

    def _execute_open_url(
        self, action: QuickLaunchAction, values: dict[str, str]
    ) -> ExecutionResult:
        url = substitute(action.url, values, quote=False).strip()
        if not url:
            return self._record_error(action, "URL 为空")
        result = self._platform.open_url(url)
        return self._record_platform_result(action, result, "open_url")

    # ----- script argv construction -----

    def _build_script_argv(
        self,
        action: QuickLaunchAction,
        path: str,
        values: dict[str, str],
    ) -> list[str]:
        interpreter_argv = self._interpreter_argv(action, values)
        extra_args_str = substitute(action.args, values, quote=False).strip()
        extra_args = shlex.split(extra_args_str) if extra_args_str else []
        return [*interpreter_argv, path, *extra_args]

    def _interpreter_argv(
        self, action: QuickLaunchAction, values: dict[str, str]
    ) -> list[str]:
        override = substitute(action.interpreter, values, quote=False).strip()
        if override:
            return shlex.split(override)
        if action.script_type in SCRIPT_INTERPRETERS:
            return list(SCRIPT_INTERPRETERS[action.script_type])
        # "other" without explicit interpreter → execute directly via shell
        return ["/bin/zsh"]

    # ----- dispatch -----

    def _dispatch_capture(
        self,
        action: QuickLaunchAction,
        argv: list[str],
        *,
        cwd: str | None,
        env: dict[str, str] | None,
    ) -> ExecutionResult:
        started_at = self._now()
        start_ts = perf_counter()
        timeout = action.timeout_sec if action.timeout_sec and action.timeout_sec > 0 else None
        capture = action.feedback_mode != "silent"
        try:
            completed = self._subprocess_run(
                argv,
                cwd=cwd or None,
                env=env,
                timeout=timeout,
                capture=capture,
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((perf_counter() - start_ts) * 1000)
            finished_at = self._now()
            run = self._repository.record_run(
                action_id=action.id,
                status="timeout",
                exit_code=None,
                stdout=self._coerce_stream(exc.stdout) if capture else "",
                stderr=self._coerce_stream(exc.stderr) if capture else "",
                duration_ms=duration_ms,
                started_at=started_at,
                finished_at=finished_at,
                message=f"执行超时 ({action.timeout_sec}s)",
            )
            return ExecutionResult(ok=False, status="timeout", message=run.message, run=run)
        except FileNotFoundError as exc:
            return self._record_error(action, f"找不到可执行文件: {exc}")
        except OSError as exc:
            return self._record_error(action, f"执行失败: {exc}")

        duration_ms = int((perf_counter() - start_ts) * 1000)
        finished_at = self._now()
        exit_code = int(completed.returncode)
        status = "success" if exit_code == 0 else "failed"
        stdout = self._coerce_stream(getattr(completed, "stdout", "")) if capture else ""
        stderr = self._coerce_stream(getattr(completed, "stderr", "")) if capture else ""
        run = self._repository.record_run(
            action_id=action.id,
            status=status,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            started_at=started_at,
            finished_at=finished_at,
            message="" if status == "success" else f"退出码 {exit_code}",
        )
        return ExecutionResult(ok=status == "success", status=status, message=run.message, run=run)

    # ----- helpers -----

    def _resolve_cwd(self, action: QuickLaunchAction, values: dict[str, str]) -> str | None:
        cwd = substitute(action.cwd, values, quote=False).strip()
        return cwd or None

    def _resolve_env(
        self, action: QuickLaunchAction, values: dict[str, str]
    ) -> dict[str, str] | None:
        if not action.env:
            return None
        merged = os.environ.copy()
        substituted = substitute_mapping(action.env, values, quote=False)
        merged.update({str(k): str(v) for k, v in substituted.items()})
        return merged

    @staticmethod
    def _coerce_stream(data: object) -> str:
        if data is None:
            return ""
        if isinstance(data, bytes):
            return data.decode("utf-8", errors="replace")
        return str(data)

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _record_error(self, action: QuickLaunchAction, message: str) -> ExecutionResult:
        now = self._now()
        run = self._repository.record_run(
            action_id=action.id,
            status="error",
            exit_code=None,
            stdout="",
            stderr=message,
            duration_ms=0,
            started_at=now,
            finished_at=now,
            message=message,
        )
        return ExecutionResult(ok=False, status="error", message=message, run=run)

    def _record_platform_result(
        self,
        action: QuickLaunchAction,
        result: object,
        kind: str,
    ) -> ExecutionResult:
        ok = bool(getattr(result, "ok", False))
        message = str(getattr(result, "message", "") or "")
        now = self._now()
        run = self._repository.record_run(
            action_id=action.id,
            status="success" if ok else "error",
            exit_code=None,
            stdout="",
            stderr="" if ok else message,
            duration_ms=0,
            started_at=now,
            finished_at=now,
            message=message or kind,
        )
        return ExecutionResult(ok=ok, status="success" if ok else "error", message=message, run=run)

    def _emit_notification(self, action: QuickLaunchAction, result: ExecutionResult) -> None:
        title = action.name or "快速启动"
        if result.ok:
            body = f"执行成功 · {action.name}"
        else:
            body = result.message or f"执行失败 · {result.status}"
        try:
            self._notification_runner(title=title, body=body, success=result.ok)
        except Exception:
            pass

    @staticmethod
    def _default_subprocess_run(argv, *, cwd, env, timeout, capture):
        if capture:
            return subprocess.run(
                argv, cwd=cwd, env=env, timeout=timeout,
                capture_output=True, text=True,
            )
        return subprocess.run(
            argv, cwd=cwd, env=env, timeout=timeout,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    @staticmethod
    def _default_notification_runner(*, title: str, body: str, success: bool) -> None:
        if sys.platform != "darwin":
            return
        safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
        safe_body = body.replace("\\", "\\\\").replace('"', '\\"')
        script = (
            f'display notification "{safe_body}" with title "{safe_title}" '
            f'subtitle "{"成功" if success else "失败"}"'
        )
        try:
            subprocess.Popen(
                ["osascript", "-e", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            pass

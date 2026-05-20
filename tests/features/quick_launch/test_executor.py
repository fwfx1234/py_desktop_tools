from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.storage import SQLiteDatabase

from features.quick_launch.executor import QuickLaunchExecutor
from features.quick_launch.repository import QuickLaunchRepository


@dataclass
class FakeCompleted:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


class FakePlatformResult:
    def __init__(self, ok: bool, message: str = "") -> None:
        self.ok = ok
        self.message = message


class FakePlatform:
    def __init__(self) -> None:
        self.open_path_calls: list[str] = []
        self.open_url_calls: list[str] = []
        self.path_result = FakePlatformResult(True, "ok")
        self.url_result = FakePlatformResult(True, "ok")

    def open_path(self, path):
        self.open_path_calls.append(str(path))
        return self.path_result

    def open_url(self, url):
        self.open_url_calls.append(str(url))
        return self.url_result


@pytest.fixture
def repository(tmp_path: Path) -> QuickLaunchRepository:
    db = SQLiteDatabase(tmp_path / "ql.db")
    return QuickLaunchRepository(db)


@pytest.fixture
def platform() -> FakePlatform:
    return FakePlatform()


def _make_executor(repo, platform, *, completed=None, notification=None):
    runner = MagicMock(return_value=completed or FakeCompleted())
    notif = notification or MagicMock()
    executor = QuickLaunchExecutor(
        repo, platform,
        subprocess_run=runner,
        notification_runner=notif,
    )
    return executor, runner, notif


def test_required_parameters_extracts_from_path_args_cwd_env(repository, platform) -> None:
    action = repository.create_action(
        name="A",
        kind="script",
        script_type="shell",
        path="${root}/run.sh",
        args="--msg ${msg}",
        cwd="${dir}",
        env={"KEY": "${k}"},
    )
    executor, _, _ = _make_executor(repository, platform)
    assert executor.required_parameters(action) == ["root", "msg", "dir", "k"]


def test_shell_script_uses_zsh_interpreter(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", script_type="shell", path="/tmp/run.sh"
    )
    executor, runner, _ = _make_executor(repository, platform)
    executor.execute(action)
    args = runner.call_args.args[0]
    assert args == ["/bin/zsh", "/tmp/run.sh"]


def test_node_script_uses_node_interpreter(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", script_type="node", path="/tmp/app.js", args="--port 3000"
    )
    executor, runner, _ = _make_executor(repository, platform)
    executor.execute(action)
    args = runner.call_args.args[0]
    assert args == ["node", "/tmp/app.js", "--port", "3000"]


def test_python_script_uses_python3(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", script_type="python", path="/tmp/x.py"
    )
    executor, runner, _ = _make_executor(repository, platform)
    executor.execute(action)
    args = runner.call_args.args[0]
    assert args == ["python3", "/tmp/x.py"]


def test_other_script_with_custom_interpreter(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", script_type="other", interpreter="ruby -W0", path="/tmp/x.rb"
    )
    executor, runner, _ = _make_executor(repository, platform)
    executor.execute(action)
    args = runner.call_args.args[0]
    assert args == ["ruby", "-W0", "/tmp/x.rb"]


def test_script_substitutes_parameters_into_args(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", script_type="shell", path="/tmp/run.sh", args="--env ${env}"
    )
    executor, runner, _ = _make_executor(repository, platform)
    executor.execute(action, parameters={"env": "prod"})
    args = runner.call_args.args[0]
    assert args == ["/bin/zsh", "/tmp/run.sh", "--env", "prod"]


def test_script_missing_param_records_error(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", script_type="shell", path="${dir}/x.sh"
    )
    executor, runner, _ = _make_executor(repository, platform)
    result = executor.execute(action)
    assert result.ok is False and result.status == "error"
    assert result.missing_parameters == ["dir"]
    runner.assert_not_called()


def test_script_failure_records_exit_code(repository, platform) -> None:
    action = repository.create_action(name="A", kind="script", path="/x.sh")
    executor, _, _ = _make_executor(
        repository, platform, completed=FakeCompleted(returncode=2, stderr="boom")
    )
    result = executor.execute(action)
    assert result.status == "failed"
    runs = repository.list_runs()
    assert runs[0].exit_code == 2 and "退出码 2" in runs[0].message


def test_script_timeout_recorded(repository, platform) -> None:
    action = repository.create_action(name="A", kind="script", path="/x.sh", timeout_sec=1)

    def fake_run(argv, *, cwd, env, timeout, capture):
        raise subprocess.TimeoutExpired(argv, timeout, output="partial", stderr="")

    executor = QuickLaunchExecutor(repository, platform, subprocess_run=fake_run)
    result = executor.execute(action)
    assert result.status == "timeout"


def test_open_path_invokes_platform(repository, platform) -> None:
    action = repository.create_action(name="A", kind="open_path", path="${root}/file.txt")
    executor, _, _ = _make_executor(repository, platform)
    result = executor.execute(action, parameters={"root": "/tmp"})
    assert result.ok is True
    assert platform.open_path_calls == ["/tmp/file.txt"]


def test_open_url_invokes_platform(repository, platform) -> None:
    action = repository.create_action(name="A", kind="open_url", url="https://x.test/${q}")
    executor, _, _ = _make_executor(repository, platform)
    executor.execute(action, parameters={"q": "abc"})
    assert platform.open_url_calls == ["https://x.test/abc"]


def test_silent_feedback_skips_capture_and_no_notification(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", path="/x.sh", feedback_mode="silent"
    )
    executor, runner, notif = _make_executor(
        repository, platform, completed=FakeCompleted(returncode=0, stdout="loud")
    )
    executor.execute(action)
    _, kwargs = runner.call_args
    assert kwargs["capture"] is False
    runs = repository.list_runs()
    assert runs[0].stdout == ""
    notif.assert_not_called()


def test_notification_feedback_triggers_notification(repository, platform) -> None:
    action = repository.create_action(
        name="Build", kind="script", path="/x.sh", feedback_mode="notification"
    )
    executor, _, notif = _make_executor(repository, platform)
    executor.execute(action)
    notif.assert_called_once()
    kwargs = notif.call_args.kwargs
    assert kwargs["title"] == "Build"
    assert kwargs["success"] is True


def test_popup_feedback_captures_but_no_notification(repository, platform) -> None:
    action = repository.create_action(
        name="A", kind="script", path="/x.sh", feedback_mode="popup"
    )
    executor, runner, notif = _make_executor(
        repository, platform, completed=FakeCompleted(returncode=0, stdout="hi"),
    )
    result = executor.execute(action)
    _, kwargs = runner.call_args
    assert kwargs["capture"] is True
    assert result.feedback_mode == "popup"
    notif.assert_not_called()
    runs = repository.list_runs()
    assert runs[0].stdout == "hi"

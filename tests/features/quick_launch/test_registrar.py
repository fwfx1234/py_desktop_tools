from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.commands.dynamic_command_registry import DynamicCommandRegistry
from app.platform.common.dynamic_commands import PluginCommandApi
from app.storage import SQLiteDatabase

from features.quick_launch.executor import QuickLaunchExecutor
from features.quick_launch.registrar import QuickLaunchRegistrar
from features.quick_launch.repository import QuickLaunchRepository


class _PlatformStub:
    def open_path(self, *_args, **_kwargs):
        raise AssertionError("open_path should not be called")

    def open_url(self, *_args, **_kwargs):
        raise AssertionError("open_url should not be called")


@pytest.fixture
def registry() -> DynamicCommandRegistry:
    return DynamicCommandRegistry()


@pytest.fixture
def repository(tmp_path: Path) -> QuickLaunchRepository:
    return QuickLaunchRepository(SQLiteDatabase(tmp_path / "ql.db"))


@pytest.fixture
def registrar(repository: QuickLaunchRepository, registry: DynamicCommandRegistry) -> QuickLaunchRegistrar:
    api = PluginCommandApi(registry, "quick-launch")
    executor = QuickLaunchExecutor(repository, _PlatformStub(), subprocess_run=MagicMock())
    return QuickLaunchRegistrar(repository, executor, api)


def _commands_for(registry: DynamicCommandRegistry) -> list[tuple[str, str]]:
    return [(c.command_id, c.launch_mode) for c in registry.all()]


def test_sync_all_registers_enabled_actions(repository, registrar, registry) -> None:
    a = repository.create_action(name="Build", kind="script", path="/x.sh", enabled=True)
    repository.create_action(name="Disabled", kind="script", path="/y.sh", enabled=False)
    registrar.sync_all()
    cmds = _commands_for(registry)
    assert (f"action.{a.id}", "none") in cmds
    assert len(cmds) == 1


def test_sync_all_uses_window_for_parameterized_actions(repository, registrar, registry) -> None:
    a = repository.create_action(name="Deploy", kind="script", path="/deploy.sh", args="--env ${env}")
    registrar.sync_all()
    assert _commands_for(registry) == [(f"action.{a.id}", "window")]


def test_sync_action_adds_updates_and_removes(repository, registrar, registry) -> None:
    a = repository.create_action(name="A", kind="script", path="/x.sh", enabled=True)
    registrar.sync_action(a.id)
    assert _commands_for(registry) == [(f"action.{a.id}", "none")]

    repository.update_action(a.id, args="--msg ${msg}")
    registrar.sync_action(a.id)
    assert _commands_for(registry) == [(f"action.{a.id}", "window")]

    repository.set_action_enabled(a.id, False)
    registrar.sync_action(a.id)
    assert _commands_for(registry) == []


def test_sync_all_removes_stale_entries(repository, registrar, registry) -> None:
    a = repository.create_action(name="A", kind="script", path="/a.sh")
    b = repository.create_action(name="B", kind="script", path="/b.sh")
    registrar.sync_all()
    assert len(_commands_for(registry)) == 2

    repository.delete_action(a.id)
    registrar.sync_all()
    cmds = _commands_for(registry)
    assert len(cmds) == 1 and cmds[0][0] == f"action.{b.id}"


def test_unregister_all_clears_registry(repository, registrar, registry) -> None:
    repository.create_action(name="A", kind="script", path="/a.sh")
    repository.create_action(name="B", kind="script", path="/b.sh")
    registrar.sync_all()
    assert len(_commands_for(registry)) == 2
    registrar.unregister_all()
    assert _commands_for(registry) == []

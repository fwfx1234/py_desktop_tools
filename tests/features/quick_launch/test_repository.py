from __future__ import annotations

from pathlib import Path

import pytest

from app.storage import SQLiteDatabase

from features.quick_launch.repository import QuickLaunchRepository


@pytest.fixture
def repository(tmp_path: Path) -> QuickLaunchRepository:
    db = SQLiteDatabase(tmp_path / "quick_launch.db")
    return QuickLaunchRepository(db)


def test_action_crud_and_enabled_filter(repository: QuickLaunchRepository) -> None:
    a1 = repository.create_action(
        name="Build", kind="script", script_type="shell", path="/bin/build.sh", enabled=True
    )
    a2 = repository.create_action(
        name="Test", kind="script", script_type="python", path="/bin/test.py", enabled=False
    )

    all_items = repository.list_actions()
    assert {item.id for item in all_items} == {a1.id, a2.id}

    enabled_items = repository.list_actions(enabled=True)
    assert [item.id for item in enabled_items] == [a1.id]

    updated = repository.update_action(a1.id, args="--clean", keywords=["build", "make"])
    assert updated is not None
    assert updated.args == "--clean"
    assert updated.keywords == ["build", "make"]

    toggled = repository.set_action_enabled(a2.id, True)
    assert toggled is not None and toggled.enabled is True

    assert repository.delete_action(a1.id) is True
    assert repository.get_action(a1.id) is None


def test_action_kinds_and_script_types(repository: QuickLaunchRepository) -> None:
    shell = repository.create_action(name="A", kind="script", script_type="shell", path="/a.sh")
    node = repository.create_action(name="B", kind="script", script_type="node", path="/b.js")
    py = repository.create_action(name="C", kind="script", script_type="python", path="/c.py")
    other = repository.create_action(
        name="D", kind="script", script_type="other", interpreter="ruby", path="/d.rb"
    )
    op = repository.create_action(name="E", kind="open_path", path="/some/dir")
    url = repository.create_action(name="F", kind="open_url", url="https://example.com")

    fetched = {a.name: a for a in repository.list_actions()}
    assert fetched["A"].script_type == "shell"
    assert fetched["B"].script_type == "node"
    assert fetched["C"].script_type == "python"
    assert fetched["D"].interpreter == "ruby"
    assert fetched["E"].kind == "open_path"
    assert fetched["F"].kind == "open_url" and fetched["F"].url == "https://example.com"


def test_action_sort_order_auto_increments(repository: QuickLaunchRepository) -> None:
    a = repository.create_action(name="A", kind="script", path="/a")
    b = repository.create_action(name="B", kind="script", path="/b")
    c = repository.create_action(name="C", kind="script", path="/c")
    orders = [item.sort_order for item in repository.list_actions()]
    assert orders == sorted(orders)
    assert a.sort_order < b.sort_order < c.sort_order


def test_action_env_and_json_roundtrip(repository: QuickLaunchRepository) -> None:
    action = repository.create_action(
        name="EnvAction",
        kind="script",
        script_type="shell",
        path="/run.sh",
        env={"K": "V", "A": "B"},
        keywords=["x", "y"],
        prefixes=["p"],
    )
    fetched = repository.get_action(action.id)
    assert fetched is not None
    assert fetched.env == {"K": "V", "A": "B"}
    assert fetched.keywords == ["x", "y"]
    assert fetched.prefixes == ["p"]


def test_record_run_truncates_large_streams(repository: QuickLaunchRepository) -> None:
    action = repository.create_action(name="A", kind="script", path="/x")
    big = "x" * (100 * 1024)
    run = repository.record_run(
        action_id=action.id,
        status="success",
        exit_code=0,
        stdout=big,
        stderr="",
        duration_ms=10,
        started_at="2026-05-20 12:00:00",
        finished_at="2026-05-20 12:00:01",
    )
    assert len(run.stdout.encode("utf-8")) <= 64 * 1024
    assert "stdout truncated" in run.message


def test_list_runs_orders_desc_and_filters(repository: QuickLaunchRepository) -> None:
    a1 = repository.create_action(name="A1", kind="script", path="/a")
    a2 = repository.create_action(name="A2", kind="script", path="/b")
    for i in range(3):
        repository.record_run(
            action_id=a1.id, status="success", exit_code=0,
            stdout="", stderr="", duration_ms=i, started_at="t", finished_at="t",
        )
    repository.record_run(
        action_id=a2.id, status="failed", exit_code=1,
        stdout="", stderr="boom", duration_ms=5, started_at="t", finished_at="t",
    )

    all_runs = repository.list_runs(limit=10)
    assert len(all_runs) == 4
    assert all_runs[0].action_id == a2.id

    just_a1 = repository.list_runs(action_id=a1.id, limit=10)
    assert len(just_a1) == 3
    assert all(run.action_id == a1.id for run in just_a1)


def test_trim_runs_keeps_latest(repository: QuickLaunchRepository) -> None:
    action = repository.create_action(name="A", kind="script", path="/x")
    for _ in range(10):
        repository.record_run(
            action_id=action.id, status="success", exit_code=0,
            stdout="", stderr="", duration_ms=0, started_at="t", finished_at="t",
        )
    removed = repository.trim_runs(keep_latest=4)
    assert removed == 6
    assert len(repository.list_runs(limit=20)) == 4

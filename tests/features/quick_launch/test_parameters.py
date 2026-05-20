from __future__ import annotations

import pytest

from features.quick_launch.parameters import (
    MissingParameterError,
    extract_parameters,
    substitute,
    substitute_mapping,
)


def test_extract_parameters_dedupes_and_preserves_order() -> None:
    specs = extract_parameters("git checkout ${branch}", "echo ${branch} ${msg}", "")
    assert [s.name for s in specs] == ["branch", "msg"]


def test_extract_parameters_ignores_invalid_names() -> None:
    specs = extract_parameters("hello $name", "ok ${1abc}", "good ${x_1}")
    assert [s.name for s in specs] == ["x_1"]


def test_substitute_quotes_shell_values() -> None:
    result = substitute("echo ${msg}", {"msg": "hi world"}, quote=True)
    assert result == "echo 'hi world'"


def test_substitute_no_quote_for_paths() -> None:
    result = substitute("${dir}/log.txt", {"dir": "/tmp/a b"}, quote=False)
    assert result == "/tmp/a b/log.txt"


def test_substitute_missing_raises_strict() -> None:
    with pytest.raises(MissingParameterError) as exc:
        substitute("echo ${a} ${b} ${a}", {"a": "x"}, quote=False)
    assert exc.value.missing == ["b"]


def test_substitute_missing_silent_when_not_strict() -> None:
    result = substitute("echo ${a} ${b}", {"a": "x"}, quote=False, strict=False)
    assert result == "echo x "


def test_substitute_mapping_quotes_values() -> None:
    env = substitute_mapping({"KEY": "${val}"}, {"val": "a b"}, quote=True)
    assert env == {"KEY": "'a b'"}

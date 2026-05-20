from __future__ import annotations

import pytest

from features.api_test.request_editor_state import (
    build_cookie_text,
    build_header_text,
    build_kv_text,
    empty_form_row,
    empty_kv_row,
    normalize_rows,
    parse_cookie_rows,
    parse_header_rows,
    parse_kv,
)
from features.api_test.service import ApiTestService


class TestParseKeyValueText:
    def test_parse_empty_string(self) -> None:
        assert ApiTestService._parse_key_value_text("") == {}
        assert ApiTestService._parse_key_value_text("   \n  \n ") == {}

    def test_parse_colon_separator(self) -> None:
        result = ApiTestService._parse_key_value_text("Content-Type: application/json")
        assert result == {"Content-Type": "application/json"}

    def test_parse_equals_separator(self) -> None:
        result = ApiTestService._parse_key_value_text("page=1")
        assert result == {"page": "1"}

    def test_parse_multiple_lines(self) -> None:
        result = ApiTestService._parse_key_value_text(
            "Content-Type: application/json\nAuthorization: Bearer token123\nX-Custom: value"
        )
        assert result == {
            "Content-Type": "application/json",
            "Authorization": "Bearer token123",
            "X-Custom": "value",
        }

    def test_parse_line_without_separator_is_skipped(self) -> None:
        result = ApiTestService._parse_key_value_text("just a comment\nkey: value")
        assert result == {"key": "value"}

    def test_parse_key_with_spaces_trimmed(self) -> None:
        result = ApiTestService._parse_key_value_text("  key  :  value  ")
        assert result == {"key": "value"}

    def test_parse_empty_key_is_skipped(self) -> None:
        result = ApiTestService._parse_key_value_text(": value\nactual_key: value2")
        assert result == {"actual_key": "value2"}

    def test_parse_colon_takes_priority_over_equals(self) -> None:
        result = ApiTestService._parse_key_value_text("key: val=ue")
        assert result == {"key": "val=ue"}


class TestParseKv:
    def test_empty_string(self) -> None:
        assert parse_kv("") == []

    def test_single_colon_line(self) -> None:
        result = parse_kv("name: Alice")
        assert len(result) == 1
        assert result[0]["key"] == "name"
        assert result[0]["value"] == "Alice"
        assert result[0]["enabled"] is True

    def test_multiple_lines(self) -> None:
        result = parse_kv("name: Alice\nage: 30")
        assert len(result) == 2
        assert result[0]["key"] == "name"
        assert result[1]["key"] == "age"

    def test_skip_empty_lines(self) -> None:
        result = parse_kv("\n\nname: Alice\n\nage: 30\n")
        assert len(result) == 2


class TestParseHeaderRows:
    def test_parse_headers(self) -> None:
        result = parse_header_rows("Content-Type: application/json\nX-Token: abc")
        assert len(result) == 2
        assert result[0]["key"] == "Content-Type"
        assert result[0]["value"] == "application/json"


class TestParseCookieRows:
    def test_semicolon_separated(self) -> None:
        result = parse_cookie_rows("session=abc123; token=xyz")
        assert len(result) == 2
        assert result[0]["key"] == "session"
        assert result[0]["value"] == "abc123"

    def test_single_cookie(self) -> None:
        result = parse_cookie_rows("session=abc123")
        assert len(result) == 1
        assert result[0]["key"] == "session"
        assert result[0]["value"] == "abc123"

    def test_empty_string(self) -> None:
        assert parse_cookie_rows("") == []


class TestNormalizeRows:
    def test_empty_appends_template(self) -> None:
        result = normalize_rows([], empty_kv_row())
        assert len(result) == 1
        assert result[0]["key"] == ""

    def test_removes_trailing_empty_pairs(self) -> None:
        rows = [
            {"enabled": True, "key": "name", "value": "Alice"},
            {"enabled": False, "key": "", "value": ""},
            {"enabled": False, "key": "", "value": ""},
        ]
        result = normalize_rows(rows, empty_kv_row())
        assert len(result) == 2

    def test_preserves_empty_row_when_previous_has_content(self) -> None:
        rows = [
            {"enabled": True, "key": "name", "value": "Alice"},
            {"enabled": False, "key": "", "value": ""},
        ]
        result = normalize_rows(rows, empty_kv_row())
        assert len(result) == 2

    def test_sets_enabled_when_key_present(self) -> None:
        rows = [{"key": "name", "value": "Alice"}]
        result = normalize_rows(rows, empty_kv_row())
        assert result[0]["enabled"] is True

    def test_sets_enabled_when_value_present(self) -> None:
        rows = [{"key": "", "value": "Alice"}]
        result = normalize_rows(rows, empty_kv_row())
        assert result[0]["enabled"] is True


class TestBuildKvText:
    def test_simple_key_value(self) -> None:
        items = [{"enabled": True, "key": "name", "value": "Alice"}]
        assert build_kv_text(items) == "name:Alice"

    def test_skips_disabled(self) -> None:
        items = [
            {"enabled": True, "key": "name", "value": "Alice"},
            {"enabled": False, "key": "secret", "value": "xxx"},
        ]
        assert build_kv_text(items) == "name:Alice"

    def test_empty_key_is_skipped(self) -> None:
        items = [{"enabled": True, "key": "", "value": "Alice"}]
        assert build_kv_text(items) == ""


class TestBuildHeaderText:
    def test_header_format_has_space_after_colon(self) -> None:
        items = [{"enabled": True, "key": "Content-Type", "value": "application/json"}]
        assert build_header_text(items) == "Content-Type: application/json"


class TestBuildCookieText:
    def test_cookie_semicolon_separated(self) -> None:
        items = [
            {"enabled": True, "key": "session", "value": "abc"},
            {"enabled": True, "key": "token", "value": "xyz"},
        ]
        assert build_cookie_text(items) == "session=abc; token=xyz"

    def test_skips_empty_key(self) -> None:
        items = [{"enabled": True, "key": "", "value": "val"}]
        assert build_cookie_text(items) == ""

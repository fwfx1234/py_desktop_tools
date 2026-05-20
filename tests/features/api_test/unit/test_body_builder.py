from __future__ import annotations

import pytest

from features.api_test.request_sender import RequestSenderCoordinator


class TestFormBodyBuilding:
    def test_empty_rows(self) -> None:
        assert RequestSenderCoordinator._build_form_body([]) == ""

    def test_non_list_input(self) -> None:
        assert RequestSenderCoordinator._build_form_body(None) == ""
        assert RequestSenderCoordinator._build_form_body("string") == ""

    def test_single_row(self) -> None:
        rows = [{"enabled": True, "key": "name", "value": "Alice"}]
        result = RequestSenderCoordinator._build_form_body(rows)
        assert "name=Alice" in result

    def test_url_encoded(self) -> None:
        rows = [{"enabled": True, "key": "name", "value": "Alice Bob"}]
        result = RequestSenderCoordinator._build_form_body(rows)
        assert "name=Alice+Bob" in result or "name=Alice%20Bob" in result

    def test_skips_disabled_rows(self) -> None:
        rows = [
            {"enabled": True, "key": "a", "value": "1"},
            {"enabled": False, "key": "b", "value": "2"},
        ]
        result = RequestSenderCoordinator._build_form_body(rows)
        assert "b=2" not in result

    def test_skips_empty_key(self) -> None:
        rows = [{"enabled": True, "key": "", "value": "val"}]
        assert RequestSenderCoordinator._build_form_body(rows) == ""

    def test_multiple_rows(self) -> None:
        rows = [
            {"enabled": True, "key": "page", "value": "1"},
            {"enabled": True, "key": "size", "value": "10"},
        ]
        result = RequestSenderCoordinator._build_form_body(rows)
        assert "page=1" in result
        assert "size=10" in result


class TestEnsureHeader:
    def test_add_header_to_empty(self) -> None:
        result = RequestSenderCoordinator._ensure_header("", "Content-Type", "application/json")
        assert result == "Content-Type: application/json"

    def test_add_to_existing_headers(self) -> None:
        result = RequestSenderCoordinator._ensure_header(
            "X-Custom: value", "Content-Type", "application/json"
        )
        assert result == "X-Custom: value\nContent-Type: application/json"

    def test_existing_header_not_duplicated(self) -> None:
        result = RequestSenderCoordinator._ensure_header(
            "Content-Type: text/html", "Content-Type", "application/json"
        )
        assert result == "Content-Type: text/html"

    def test_case_insensitive_match(self) -> None:
        result = RequestSenderCoordinator._ensure_header(
            "content-type: text/html", "Content-Type", "application/json"
        )
        assert result == "content-type: text/html"


class TestHasHeader:
    def test_header_present(self) -> None:
        assert RequestSenderCoordinator._has_header("Content-Type: json", "Content-Type") is True

    def test_header_absent(self) -> None:
        assert RequestSenderCoordinator._has_header("X-Custom: val", "Content-Type") is False

    def test_case_insensitive(self) -> None:
        assert RequestSenderCoordinator._has_header("content-type: json", "Content-Type") is True

    def test_empty_text(self) -> None:
        assert RequestSenderCoordinator._has_header("", "Content-Type") is False

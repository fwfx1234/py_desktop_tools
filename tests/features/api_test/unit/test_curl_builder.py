from __future__ import annotations

import pytest

from features.api_test.http_service import HttpRequestService


class TestShellQuote:
    def test_simple_string(self) -> None:
        assert HttpRequestService._shell_quote("hello") == "'hello'"

    def test_empty_string(self) -> None:
        assert HttpRequestService._shell_quote("") == "''"

    def test_string_with_single_quote(self) -> None:
        result = HttpRequestService._shell_quote("it's")
        assert result == "'it'\"'\"'s'"

    def test_string_with_spaces(self) -> None:
        result = HttpRequestService._shell_quote("hello world")
        assert result == "'hello world'"


class TestToCurl:
    def test_basic_get_request(self) -> None:
        result = HttpRequestService._to_curl("GET", "http://example.com", {}, "")
        assert result == "curl -X 'GET' 'http://example.com'"

    def test_request_with_headers(self) -> None:
        result = HttpRequestService._to_curl(
            "POST",
            "http://example.com",
            {"Content-Type": "application/json"},
            "",
        )
        assert "-H 'Content-Type: application/json'" in result
        assert "-X 'POST'" in result

    def test_content_length_header_is_skipped(self) -> None:
        result = HttpRequestService._to_curl(
            "POST",
            "http://example.com",
            {"Content-Type": "application/json", "Content-Length": "100"},
            "",
        )
        assert "Content-Length" not in result

    def test_request_with_body(self) -> None:
        result = HttpRequestService._to_curl(
            "POST",
            "http://example.com",
            {"Content-Type": "application/json"},
            '{"key": "value"}',
        )
        assert "--data-raw" in result

    def test_method_in_output(self) -> None:
        result = HttpRequestService._to_curl("DELETE", "http://example.com/resource", {}, "")
        assert "-X 'DELETE'" in result


class TestAppendQuery:
    def test_no_params(self) -> None:
        assert HttpRequestService._append_query("http://example.com", {}) == "http://example.com"

    def test_with_params_no_existing_query(self) -> None:
        result = HttpRequestService._append_query(
            "http://example.com", {"page": "1", "size": "10"}
        )
        assert "?" in result
        assert "page=1" in result
        assert "size=10" in result

    def test_with_params_existing_query(self) -> None:
        result = HttpRequestService._append_query(
            "http://example.com?token=abc", {"page": "1"}
        )
        assert "&page=1" in result

    def test_empty_url(self) -> None:
        result = HttpRequestService._append_query("", {"key": "val"})
        assert "key=val" in result


class TestBodyToText:
    def test_none_body(self) -> None:
        assert HttpRequestService._body_to_text(None) == ""

    def test_bytes_body(self) -> None:
        assert HttpRequestService._body_to_text(b"hello") == "hello"

    def test_str_body(self) -> None:
        assert HttpRequestService._body_to_text("hello") == "hello"

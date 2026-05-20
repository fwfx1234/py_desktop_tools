from __future__ import annotations

import pytest

from features.api_test.http_service import HttpRequestService
from features.api_test.service import ApiTestService


class TestPathParamKeys:
    def test_single_key(self) -> None:
        assert ApiTestService._path_param_keys("/api/users/{id}") == {"id"}

    def test_multiple_keys(self) -> None:
        assert ApiTestService._path_param_keys("/api/{org}/users/{id}") == {"org", "id"}

    def test_no_keys(self) -> None:
        assert ApiTestService._path_param_keys("/api/users") == set()

    def test_empty_url(self) -> None:
        assert ApiTestService._path_param_keys("") == set()
        assert ApiTestService._path_param_keys(None) == set()

    def test_malformed_brackets_ignored(self) -> None:
        assert ApiTestService._path_param_keys("/api/{unclosed") == set()
        assert ApiTestService._path_param_keys("/api/unopened}") == set()

    def test_multiple_keys_with_separators(self) -> None:
        result = ApiTestService._path_param_keys("{outer}_inner_{another}")
        assert result == {"outer", "another"}

    def test_empty_key_skipped(self) -> None:
        assert ApiTestService._path_param_keys("/api/{}") == set()


class TestApplyPathParams:
    def test_replace_single_param(self) -> None:
        result = ApiTestService._apply_path_params("/api/users/{id}", {"id": "123"})
        assert result == "/api/users/123"

    def test_replace_multiple_params(self) -> None:
        result = ApiTestService._apply_path_params(
            "/api/{org}/users/{id}", {"org": "acme", "id": "456"}
        )
        assert result == "/api/acme/users/456"

    def test_longest_key_matched_first(self) -> None:
        result = ApiTestService._apply_path_params(
            "/api/{id}/{user_id}", {"id": "1", "user_id": "99"}
        )
        assert result == "/api/1/99"

    def test_unmatched_keys_remain(self) -> None:
        result = ApiTestService._apply_path_params("/api/{name}", {})
        assert result == "/api/{name}"

    def test_url_encoding_applied(self) -> None:
        result = ApiTestService._apply_path_params(
            "/api/{name}", {"name": "hello world"}
        )
        assert result == "/api/hello%20world"


class TestResolveUrl:
    def test_absolute_url_bypasses_base(self) -> None:
        result = HttpRequestService._resolve_url(
            "https://api.example.com/users", "http://localhost:8000"
        )
        assert result == "https://api.example.com/users"

    def test_relative_with_leading_slash(self) -> None:
        result = HttpRequestService._resolve_url("/api/users", "http://localhost:8000")
        assert result == "http://localhost:8000/api/users"

    def test_relative_without_leading_slash(self) -> None:
        result = HttpRequestService._resolve_url("api/users", "http://localhost:8000")
        assert result == "http://localhost:8000/api/users"

    def test_empty_url_returns_base(self) -> None:
        result = HttpRequestService._resolve_url("", "http://localhost:8000")
        assert result == "http://localhost:8000"

    def test_empty_base_treated_as_absolute(self) -> None:
        result = HttpRequestService._resolve_url("/api/users", "")
        assert result == "/api/users"

    def test_base_with_trailing_slash(self) -> None:
        result = HttpRequestService._resolve_url("/users", "http://localhost:8000/")
        assert result == "http://localhost:8000/users"

    def test_https_absolute_bypasses_base(self) -> None:
        result = HttpRequestService._resolve_url(
            "https://secure.example.com", "http://localhost"
        )
        assert result == "https://secure.example.com"

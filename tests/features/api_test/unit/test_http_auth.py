from __future__ import annotations

import pytest

from features.api_test.service import ApiTestService


class TestApplyAuth:
    def test_none_auth_type_preserves_headers(self) -> None:
        headers = {"Content-Type": "application/json"}
        result = ApiTestService._apply_auth(headers, "none", "anything")
        assert result == headers
        assert result is not headers  # returns a copy

    def test_bearer_auth(self) -> None:
        result = ApiTestService._apply_auth({}, "bearer", "my-token")
        assert result == {"Authorization": "Bearer my-token"}

    def test_bearer_case_insensitive(self) -> None:
        result = ApiTestService._apply_auth({}, "BEARER", "my-token")
        assert result == {"Authorization": "Bearer my-token"}

    def test_bearer_with_empty_value_does_not_add_header(self) -> None:
        result = ApiTestService._apply_auth({}, "bearer", "  ")
        assert "Authorization" not in result

    def test_basic_auth_encodes_credentials(self) -> None:
        result = ApiTestService._apply_auth({}, "basic", "user:pass")
        assert result["Authorization"].startswith("Basic ")
        import base64

        decoded = base64.b64decode(result["Authorization"][6:]).decode("utf-8")
        assert decoded == "user:pass"

    def test_basic_auth_already_encoded_passed_through(self) -> None:
        already_encoded = "dXNlcjpwYXNz"
        result = ApiTestService._apply_auth({}, "basic", already_encoded)
        assert result["Authorization"] == f"Basic {already_encoded}"

    def test_apikey_auth(self) -> None:
        result = ApiTestService._apply_auth({}, "apikey", "key-12345")
        assert result == {"X-API-Key": "key-12345"}

    def test_auth_merges_with_existing_headers(self) -> None:
        headers = {"Content-Type": "application/json"}
        result = ApiTestService._apply_auth(headers, "bearer", "token")
        assert result["Content-Type"] == "application/json"
        assert result["Authorization"] == "Bearer token"

    def test_bearer_overwrites_existing_authorization(self) -> None:
        headers = {"Authorization": "old"}
        result = ApiTestService._apply_auth(headers, "bearer", "new-token")
        assert result["Authorization"] == "Bearer new-token"

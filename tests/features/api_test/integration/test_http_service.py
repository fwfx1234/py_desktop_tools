from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from features.api_test.http_service import HttpRequestService
from features.api_test.script_service import ScriptService
from features.api_test.variable_service import VariableService


class TestHttpRequestService:
    @pytest.fixture
    def http_svc(self, variable_service) -> HttpRequestService:
        return HttpRequestService(variable_service, ScriptService())

    def test_build_request_details_basic(self, http_svc: HttpRequestService) -> None:
        details = http_svc.build_request_details(
            method="GET",
            url="http://example.com/api",
            params={},
            headers={},
            body_text="",
        )
        assert "requestText" in details
        assert "curlText" in details
        assert details["curlText"].startswith("curl")

    def test_send_request_success(self, http_svc: HttpRequestService) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"ok": true}'
        mock_response.text = '{"ok": true}'
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.url = "http://example.com/api"
        mock_response.elapsed.total_seconds.return_value = 0.05
        mock_response.request = MagicMock()
        mock_response.request.method = "GET"
        mock_response.request.url = "http://example.com/api"
        mock_response.request.headers = {"Content-Type": "application/json"}
        mock_response.request.body = None
        mock_response.json.return_value = {"ok": True}

        with patch("requests.request", return_value=mock_response):
            title, body, status_code, final_url, details = http_svc.send(
                method="GET",
                url="http://example.com/api",
                params={},
                headers={},
                body_text="",
                env_name="",
                env_base_url="",
                pre_ops_text="",
                assertions_text="",
            )

        assert status_code == 200
        assert "200" in title
        assert details["statusCode"] == "200"

    def test_send_request_connection_error(self, http_svc: HttpRequestService) -> None:
        import requests

        with patch("requests.request", side_effect=requests.ConnectionError("Connection refused")):
            title, body, status_code, final_url, details = http_svc.send(
                method="GET",
                url="http://localhost:9999/api",
                params={},
                headers={},
                body_text="",
                env_name="",
                env_base_url="",
                pre_ops_text="",
                assertions_text="",
            )

        assert "ERR" in title
        assert "连接失败" in title

    def test_send_request_timeout(self, http_svc: HttpRequestService) -> None:
        import requests

        with patch("requests.request", side_effect=requests.Timeout("Request timed out")):
            title, body, status_code, final_url, details = http_svc.send(
                method="GET", url="http://example.com/api",
                params={}, headers={}, body_text="",
                env_name="", env_base_url="",
                pre_ops_text="", assertions_text="",
            )

        assert "超时" in title

    def test_send_resolves_variables_in_url(self, http_svc: HttpRequestService) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"ok": true}'
        mock_response.text = '{"ok": true}'
        mock_response.headers = {}
        mock_response.url = "http://api.example.com/v1/users"
        mock_response.elapsed.total_seconds.return_value = 0.01
        mock_response.request = MagicMock()
        mock_response.request.method = "GET"
        mock_response.request.url = "http://api.example.com/v1/users"
        mock_response.request.headers = {}
        mock_response.request.body = None
        mock_response.json.return_value = {"ok": True}

        with patch("requests.request", return_value=mock_response) as mock_req:
            http_svc.send(
                method="GET",
                url="{{base_url}}/users",
                params={},
                headers={},
                body_text="",
                env_name="",
                env_base_url="http://api.example.com",
                pre_ops_text="set base_url=v1",
                assertions_text="",
                env_vars={},
            )

    def test_send_resolves_variables_in_headers(self, http_svc: HttpRequestService) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"ok": true}'
        mock_response.text = '{"ok": true}'
        mock_response.headers = {}
        mock_response.url = "http://example.com/api"
        mock_response.elapsed.total_seconds.return_value = 0.01
        mock_response.request = MagicMock()
        mock_response.request.method = "GET"
        mock_response.request.url = "http://example.com/api"
        mock_response.request.headers = {"Authorization": "Bearer prod-token"}
        mock_response.request.body = None
        mock_response.json.return_value = {"ok": True}

        with patch("requests.request", return_value=mock_response):
            http_svc.send(
                method="GET",
                url="http://example.com/api",
                params={},
                headers={"Authorization": "Bearer {{token}}"},
                body_text="",
                env_name="prod",
                env_base_url="",
                pre_ops_text="",
                assertions_text="",
                env_vars={"token": "prod-token"},
            )

    def test_send_includes_assertions_in_response(self, http_svc: HttpRequestService) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"code": 200}'
        mock_response.text = '{"code": 200}'
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.url = "http://example.com/api"
        mock_response.elapsed.total_seconds.return_value = 0.01
        mock_response.request = MagicMock()
        mock_response.request.method = "GET"
        mock_response.request.url = "http://example.com/api"
        mock_response.request.headers = {}
        mock_response.request.body = None
        mock_response.json.return_value = {"code": 200}

        with patch("requests.request", return_value=mock_response):
            _, body, _, _, _ = http_svc.send(
                method="GET",
                url="http://example.com/api",
                params={},
                headers={},
                body_text="",
                env_name="",
                env_base_url="",
                pre_ops_text="",
                assertions_text="status == 200",
            )

        assert "--- Assertions ---" in body
        assert "PASS" in body

    def test_send_file_missing_file(self, http_svc: HttpRequestService) -> None:
        title, body, status_code, final_url, details = http_svc.send_file(
            method="POST",
            url="http://example.com/upload",
            params={},
            headers={},
            file_path="/nonexistent/file.txt",
            file_param="file",
            env_name="",
            env_base_url="",
            pre_ops_text="",
            assertions_text="",
        )
        assert "ERR" in title
        assert body == f"文件不存在: /nonexistent/file.txt"

    def test_resolve_url_absolute(self, http_svc: HttpRequestService) -> None:
        assert HttpRequestService._resolve_url(
            "https://api.example.com/users", "http://localhost"
        ) == "https://api.example.com/users"

    def test_prepare_request(self, http_svc: HttpRequestService) -> None:
        from features.api_test.script_service import RequestDraft

        draft = RequestDraft(
            method="POST",
            url="http://example.com/api",
            params={"page": "1"},
            headers={"Content-Type": "application/json"},
            body='{"key": "value"}',
        )
        prepared = HttpRequestService._prepare_request(draft)
        assert prepared.method == "POST"
        assert "page=1" in prepared.url
        assert prepared.headers["Content-Type"] == "application/json"

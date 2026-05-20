from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from features.api_test.request_sender import RequestSenderCoordinator
from features.api_test.service import ApiTestService


class TestRequestSenderLifecycle:
    @pytest.fixture
    def make_sender(self):
        def _make(task_runner=None):
            service = MagicMock(spec=ApiTestService)
            on_response = MagicMock()
            on_history = MagicMock()
            on_sending = MagicMock()
            on_ws_timeline = MagicMock()
            on_ws_status = MagicMock()

            sender = RequestSenderCoordinator(
                service,
                on_response=on_response,
                on_history=on_history,
                on_sending=on_sending,
                on_ws_timeline=on_ws_timeline,
                on_ws_status=on_ws_status,
                task_runner=task_runner,
            )
            return sender, service, on_response, on_history, on_sending

        return _make

    def test_send_request_starts_task_runner(self, make_sender) -> None:
        from app.concurrency import PythonTaskRunner

        runner = PythonTaskRunner(thread_name_prefix="test")
        sender, service, on_response, on_history, on_sending = make_sender(task_runner=runner)

        service.send_api.return_value = ("200 OK", '{"ok": true}', {"statusCode": "200"})

        data = {
            "method": "GET",
            "url": "http://example.com/api",
            "paramsText": "",
            "headersText": "",
            "bodyText": "",
            "envBaseUrl": "",
            "authType": "none",
            "authValue": "",
            "mockMode": False,
            "requestMode": "http",
            "tabId": "tab-1",
            "filePath": "",
            "fileParamName": "file",
            "cookiesText": "",
            "currentBodyMode": 0,
            "bodyFormRows": [],
            "wsEncoding": "text",
            "preOpsText": "",
            "postOpsText": "",
        }
        sender.send_request(data)

        runner.shutdown(wait=True)

        on_sending.assert_any_call(True)
        service.send_api.assert_called_once()

    def test_send_request_rejects_concurrent(self, make_sender) -> None:
        sender, service, on_response, _, on_sending = make_sender()
        # Simulate busy state by making _begin_request return ""
        sender._sending = True

        data = {
            "method": "GET", "url": "/api",
            "paramsText": "", "headersText": "", "bodyText": "",
            "envBaseUrl": "", "authType": "none", "authValue": "",
            "mockMode": False, "requestMode": "http", "tabId": "",
            "filePath": "", "fileParamName": "file", "cookiesText": "",
            "currentBodyMode": 0, "bodyFormRows": [], "wsEncoding": "text",
            "preOpsText": "", "postOpsText": "",
        }
        sender.send_request(data)

        on_response.assert_called_once()
        assert "BUSY" in on_response.call_args[0][0]

    def test_dispose_prevents_new_requests(self, make_sender) -> None:
        sender, service, on_response, _, _ = make_sender()
        sender.dispose()

        data = {
            "method": "GET", "url": "/api",
            "paramsText": "", "headersText": "", "bodyText": "",
            "envBaseUrl": "", "authType": "none", "authValue": "",
            "mockMode": False, "requestMode": "http", "tabId": "",
            "filePath": "", "fileParamName": "file", "cookiesText": "",
            "currentBodyMode": 0, "bodyFormRows": [], "wsEncoding": "text",
            "preOpsText": "", "postOpsText": "",
        }
        sender.send_request(data)
        # Should be rejected silently without on_response
        on_response.assert_not_called()

    def test_body_mode_form_builds_urlencoded_body(self, make_sender) -> None:
        from app.concurrency import PythonTaskRunner

        runner = PythonTaskRunner(thread_name_prefix="test")
        sender, service, _, _, _ = make_sender(task_runner=runner)
        service.send_api.return_value = ("OK", '{}', {})

        data = {
            "method": "POST", "url": "/api",
            "paramsText": "", "headersText": "", "bodyText": "",
            "envBaseUrl": "", "authType": "none", "authValue": "",
            "mockMode": False, "requestMode": "http", "tabId": "",
            "filePath": "", "fileParamName": "file", "cookiesText": "",
            "currentBodyMode": 1,  # form
            "bodyFormRows": [{"enabled": True, "key": "name", "value": "Alice"}],
            "wsEncoding": "text", "preOpsText": "", "postOpsText": "",
        }
        sender.send_request(data)
        runner.shutdown(wait=True)

        call_args, _ = service.send_api.call_args
        # body_text is the 5th positional argument
        assert call_args[4] == "name=Alice"

    def test_ws_request_mode(self, make_sender) -> None:
        from app.concurrency import PythonTaskRunner

        runner = PythonTaskRunner(thread_name_prefix="test")
        sender, service, _, _, _ = make_sender(task_runner=runner)
        service.ws_send.return_value = ("WS_SENT", "hello")

        data = {
            "method": "GET", "url": "ws://example.com",
            "paramsText": "", "headersText": "", "bodyText": "hello",
            "envBaseUrl": "", "authType": "none", "authValue": "",
            "mockMode": False, "requestMode": "websocket", "tabId": "ws-1",
            "filePath": "", "fileParamName": "file", "cookiesText": "",
            "currentBodyMode": 0, "bodyFormRows": [], "wsEncoding": "text",
            "preOpsText": "", "postOpsText": "",
        }
        sender.send_request(data)
        runner.shutdown(wait=True)
        service.ws_send.assert_called_once()

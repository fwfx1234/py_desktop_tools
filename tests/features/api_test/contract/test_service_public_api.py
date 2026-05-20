from __future__ import annotations

"""Contract tests verify the stability of the public API surface of ApiTestService.

These tests don't call any actual network or database — they verify that
method signatures exist and match the expected interface consumed by QML
and other Python components.
"""

import inspect

import pytest


class TestApiTestServicePublicApi:
    """Verify the public methods that QML and other code depend on."""

    SERVICE_METHODS = [
        "list_tabs",
        "list_environments",
        "save_environments",
        "load_collection_tree",
        "create_collection_node",
        "duplicate_collection_node",
        "rename_collection_node",
        "update_collection_endpoint",
        "set_collection_node_expanded",
        "save_case_snapshot",
        "set_all_collection_nodes_expanded",
        "delete_collection_node",
        "move_collection_node",
        "replace_collection_tree",
        "upsert_tab",
        "delete_tab",
        "import_openapi",
        "send_api",
        "send_api_file",
        "ws_connect",
        "ws_send",
        "ws_receive",
        "ws_disconnect",
        "ws_timeline",
        "ws_connected",
        "save_debug_case",
        "list_debug_cases",
        "run_debug_cases",
        "get_history",
        "list_history",
        "close",
    ]

    @pytest.fixture
    def service(self, api_database):
        from features.api_test.service import ApiTestService

        return ApiTestService(api_database.storage)

    def test_all_expected_methods_exist(self, service) -> None:
        for method_name in self.SERVICE_METHODS:
            assert hasattr(service, method_name), f"Missing method: {method_name}"
            method = getattr(service, method_name)
            assert callable(method), f"{method_name} is not callable"

    def test_send_api_signature(self, service) -> None:
        sig = inspect.signature(service.send_api)
        params = list(sig.parameters.keys())
        assert "method" in params
        assert "url" in params
        assert "params_text" in params
        assert "headers_text" in params
        assert "body_text" in params
        assert "env_base_url" in params

    def test_import_openapi_is_instance_method(self) -> None:
        from features.api_test.service import ApiTestService
        assert callable(ApiTestService.import_openapi)

    def test_parse_key_value_text_is_static(self) -> None:
        from features.api_test.service import ApiTestService
        assert isinstance(ApiTestService.__dict__.get("_parse_key_value_text"), staticmethod)

    def test_close_is_idempotent(self, service) -> None:
        # close() should not raise even with no active connections
        service.close()
        service.close()  # second call should also be safe


class TestHttpRequestServicePublicApi:
    def test_send_signature(self) -> None:
        from features.api_test.http_service import HttpRequestService

        sig = inspect.signature(HttpRequestService.send)
        params = list(sig.parameters.keys())
        assert "method" in params
        assert "url" in params
        assert "body_text" in params
        assert "env_name" in params

    def test_build_request_details_signature(self) -> None:
        from features.api_test.http_service import HttpRequestService

        sig = inspect.signature(HttpRequestService.build_request_details)
        params = list(sig.parameters.keys())
        expected = ["method", "url", "params", "headers", "body_text", "log_note"]
        assert all(p in params for p in expected)


class TestScriptServicePublicApi:
    def test_public_methods_exist(self) -> None:
        from features.api_test.script_service import ScriptService

        svc = ScriptService()
        assert callable(svc.apply_pre_ops)
        assert callable(svc.run_assertions)
        assert callable(svc.extract_variables)


class TestVariableServicePublicApi:
    def test_public_methods_exist(self, variable_service) -> None:
        assert callable(variable_service.resolve_text)
        assert callable(variable_service.set_variable)


class TestRequestEditorStatePublicApi:
    def test_public_methods_exist(self) -> None:
        from features.api_test.request_editor_state import RequestEditorState

        state = RequestEditorState()
        assert callable(state.normalize_section)
        assert callable(state.apply_tab)
        assert callable(state.update_tab_from_state)
        assert callable(state.set_current_body_mode)

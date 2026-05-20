from __future__ import annotations

import json

import pytest

from features.api_test.request_editor_state import (
    RequestEditorState,
    empty_form_row,
    empty_kv_row,
    snapshot_from_tab,
)


class TestRequestEditorState:
    @pytest.fixture
    def state(self) -> RequestEditorState:
        return RequestEditorState()

    def test_initial_defaults(self, state: RequestEditorState) -> None:
        assert state.body_modes == ["none", "x-www-form-urlencoded", "JSON", "XML", "Text", "file"]
        assert state.current_body_mode == 0
        assert state.mock_mode is False
        assert state.auth_type_value == "none"

    def test_current_body_mode_name(self, state: RequestEditorState) -> None:
        assert state.current_body_mode_name() == "none"
        state.current_body_mode = 2
        assert state.current_body_mode_name() == "JSON"

    def test_body_text_for_request_returns_empty_for_form_mode(self, state: RequestEditorState) -> None:
        state.current_body_mode = 1  # form
        state.body_text = "should not appear"
        assert state.body_text_for_request() == ""

    def test_body_text_for_request_returns_empty_for_file_mode(self, state: RequestEditorState) -> None:
        state.current_body_mode = 5  # file
        state.body_text = "should not appear"
        assert state.body_text_for_request() == ""

    def test_body_text_for_request_returns_text_for_json_mode(self, state: RequestEditorState) -> None:
        state.current_body_mode = 2  # JSON
        state.body_text = '{"key": "value"}'
        assert state.body_text_for_request() == '{"key": "value"}'

    def test_set_current_body_mode_saves_and_loads(self, state: RequestEditorState) -> None:
        state.current_body_mode = 2  # JSON
        state.body_text = '{"saved": true}'
        state.set_current_body_mode(0)  # none
        assert state.body_text == ""  # none mode had no saved content
        state.set_current_body_mode(2)  # back to JSON
        assert state.body_text == '{"saved": true}'

    def test_body_form_live_rows_update_current_mode_cache(self, state: RequestEditorState) -> None:
        state.current_body_mode = 1
        assert state.edit_row_key_live("body", 0, "name") is True
        assert state.edit_row_value_live("body", 0, "Alice") is True
        assert state.body_per_mode["x-www-form-urlencoded"] == [
            {"enabled": True, "key": "name", "value": "Alice"}
        ]

    def test_normalize_section_query(self, state: RequestEditorState) -> None:
        result = state.normalize_section("query")
        assert len(result) >= 1
        assert "enabled" in result[0]

    def test_normalize_section_headers(self, state: RequestEditorState) -> None:
        result = state.normalize_section("headers")
        assert len(result) >= 1

    def test_normalize_unknown_section(self, state: RequestEditorState) -> None:
        assert state.normalize_section("unknown_section") == []

    def test_toggle_row_enabled(self, state: RequestEditorState) -> None:
        state.query_params = [{"enabled": False, "key": "k", "value": "v", "type": "string", "desc": ""}]
        assert state.toggle_row_enabled("query", 0, True) is True
        assert state.query_params[0]["enabled"] is True

    def test_toggle_row_invalid_index(self, state: RequestEditorState) -> None:
        assert state.toggle_row_enabled("query", 999, True) is False

    def test_edit_row_key(self, state: RequestEditorState) -> None:
        state.query_params = [{"enabled": False, "key": "", "value": "", "type": "string", "desc": ""}]
        assert state.edit_row_key("query", 0, "new_key") is True
        assert state.query_params[0]["key"] == "new_key"
        assert state.query_params[0]["enabled"] is True

    def test_edit_row_key_appends_empty_row(self, state: RequestEditorState) -> None:
        state.query_params = [{"enabled": False, "key": "", "value": "", "type": "string", "desc": ""}]
        assert state.edit_row_key("query", 0, "new_key") is True
        assert len(state.query_params) == 2
        assert state.query_params[1] == empty_kv_row()

    def test_edit_row_key_live_does_not_append_empty_row(self, state: RequestEditorState) -> None:
        state.query_params = [{"enabled": False, "key": "", "value": "", "type": "string", "desc": ""}]
        assert state.edit_row_key_live("query", 0, "new_key") is True
        assert state.query_params == [{"enabled": True, "key": "new_key", "value": "", "type": "string", "desc": ""}]

    def test_edit_row_key_invalid_index(self, state: RequestEditorState) -> None:
        assert state.edit_row_key("query", 999, "key") is False

    def test_edit_row_value(self, state: RequestEditorState) -> None:
        state.query_params = [{"enabled": True, "key": "k", "value": "old", "type": "string", "desc": ""}]
        assert state.edit_row_value("query", 0, "new_value") is True
        assert state.query_params[0]["value"] == "new_value"

    def test_edit_row_value_live_does_not_append_empty_row(self, state: RequestEditorState) -> None:
        state.query_params = [{"enabled": True, "key": "k", "value": "", "type": "string", "desc": ""}]
        assert state.edit_row_value_live("query", 0, "new_value") is True
        assert state.query_params == [{"enabled": True, "key": "k", "value": "new_value", "type": "string", "desc": ""}]

    def test_delete_row(self, state: RequestEditorState) -> None:
        state.query_params = [
            {"enabled": True, "key": "k1", "value": "v1", "type": "string", "desc": ""},
            {"enabled": True, "key": "k2", "value": "v2", "type": "string", "desc": ""},
        ]
        assert state.delete_row("query", 0) is True
        assert len(state.query_params) >= 1

    def test_delete_row_invalid_index(self, state: RequestEditorState) -> None:
        assert state.delete_row("query", 999) is False

    def test_apply_tab_to_state(self, state: RequestEditorState) -> None:
        tab = {
            "authType": "bearer",
            "authValue": "token123",
            "headersText": "Content-Type: application/json",
            "cookiesText": "",
            "bodyText": '{"none": ""}',
            "bodyMode": "JSON",
            "preOpsText": "set token=abc",
            "postOpsText": "status == 200",
            "paramsText": "page: 1",
            "pathParamsText": "",
            "envBaseUrl": "http://test.example.com",
            "mockMode": False,
        }
        env_index = state.apply_tab(tab, [{"baseUrl": "http://test.example.com"}])
        assert state.auth_type_value == "bearer"
        assert state.auth_value_text == "token123"
        assert state.pre_ops_text == "set token=abc"
        assert env_index == 0

    def test_update_tab_from_state(self, state: RequestEditorState) -> None:
        state.auth_type_value = "bearer"
        state.auth_value_text = "token123"
        tab = {"id": "tab-1", "name": "test"}
        result = state.update_tab_from_state(tab, "http://env.example.com")
        assert result["authType"] == "bearer"
        assert result["authValue"] == "token123"
        assert result["envBaseUrl"] == "http://env.example.com"


class TestSnapshotFromTab:
    def test_snapshot_copies_all_fields(self) -> None:
        tab = {
            "name": "Test API",
            "method": "POST",
            "url": "/api/test",
            "requestMode": "http",
            "bodyMode": "JSON",
            "authType": "bearer",
            "authValue": "token",
            "headersText": "Content-Type: application/json",
            "cookiesText": "",
            "bodyText": '{"key": "value"}',
            "paramsText": "page: 1",
            "pathParamsText": "id: 123",
            "envBaseUrl": "http://localhost",
            "preOpsText": "set token=abc",
            "postOpsText": "status == 200",
            "mockMode": True,
        }
        snapshot = snapshot_from_tab(tab)
        assert snapshot["name"] == "Test API"
        assert snapshot["method"] == "POST"
        assert snapshot["bodyMode"] == "JSON"
        assert snapshot["mockMode"] is True

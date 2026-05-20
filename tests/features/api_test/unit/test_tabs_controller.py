from __future__ import annotations

import pytest

from features.api_test.request_editor_state import RequestEditorState
from features.api_test.tabs_controller import TabsController


class TestTabsController:
    @pytest.fixture
    def make_controller(self):
        def _make(items=None, current_index=0):
            editor = RequestEditorState()
            save_calls = []
            case_save_calls = []
            delete_calls = []

            ctrl = TabsController(
                editor,
                env_base_url=lambda: "http://default.example.com",
                save_tab_draft=lambda d: save_calls.append(d),
                save_case_snapshot=lambda nid, snap: case_save_calls.append((nid, snap)),
                delete_tab=lambda tid: delete_calls.append(tid),
            )
            if items:
                ctrl.set_items(items)
                ctrl.current_index = current_index
            return ctrl, editor, save_calls, case_save_calls, delete_calls

        return _make

    def test_initial_state(self, make_controller) -> None:
        ctrl, editor, _, _, _ = make_controller()
        assert ctrl.items == []
        assert ctrl.current_index == -1
        assert ctrl.current_tab() == {}
        assert ctrl.current_tab_id() == ""

    def test_set_items(self, make_controller) -> None:
        ctrl, _, _, _, _ = make_controller()
        items = [{"id": "tab-1", "name": "Test"}]
        ctrl.set_items(items)
        assert len(ctrl.items) == 1
        assert ctrl.current_index == 0

    def test_set_items_with_existing_index(self, make_controller) -> None:
        ctrl, _, _, _, _ = make_controller()
        ctrl.items = [{"id": "tab-1"}, {"id": "tab-2"}]
        ctrl.current_index = 1
        ctrl.set_items([{"id": "new-tab"}])
        assert ctrl.current_index == 0

    def test_current_tab_id(self, make_controller) -> None:
        ctrl, _, _, _, _ = make_controller()
        ctrl.set_items([{"id": "tab-123", "name": "Test"}])
        assert ctrl.current_tab_id() == "tab-123"

    def test_set_current_index(self, make_controller) -> None:
        ctrl, _, _, _, _ = make_controller()
        ctrl.set_items([
            {"id": "tab-1", "authType": "none", "bodyText": "{}"},
            {"id": "tab-2", "authType": "bearer", "authValue": "tok", "bodyText": "{}"},
        ])
        ctrl.set_current_index(1, [])
        assert ctrl.current_index == 1

    def test_same_index_noop(self, make_controller) -> None:
        ctrl, _, _, _, _ = make_controller()
        ctrl.set_items([{"id": "tab-1", "authType": "none", "bodyText": "{}"}])
        result = ctrl.set_current_index(0, [])
        assert result is None

    def test_set_current_index_persists_current_params_before_switch(self, make_controller) -> None:
        ctrl, editor, save_calls, _, _ = make_controller()
        ctrl.set_items([
            {"id": "tab-1", "name": "A", "authType": "none", "bodyText": "{}"},
            {"id": "tab-2", "name": "B", "authType": "none", "bodyText": "{}"},
        ])
        editor.query_params = [{"enabled": True, "key": "page", "value": "1", "type": "string", "desc": ""}]

        ctrl.set_current_index(1, [])

        assert save_calls[0]["id"] == "tab-1"
        assert save_calls[0]["paramsText"] == "page:1"
        assert ctrl.items[0]["paramsText"] == "page:1"
        assert editor.query_params[0]["key"] == ""

    def test_persist_current_saves_via_callback(self, make_controller) -> None:
        ctrl, editor, save_calls, _, _ = make_controller()
        ctrl.set_items([{"id": "tab-1", "name": "Test", "authType": "none", "bodyText": "{}"}])
        editor.auth_type_value = "bearer"
        assert ctrl.persist_current() is True
        assert len(save_calls) == 1
        assert save_calls[0]["authType"] == "bearer"

    def test_persist_current_while_applying_is_noop(self, make_controller) -> None:
        ctrl, editor, save_calls, _, _ = make_controller()
        ctrl.set_items([{"id": "tab-1", "name": "Test", "authType": "none", "bodyText": "{}"}])
        ctrl.applying = True
        assert ctrl.persist_current() is False
        assert len(save_calls) == 0

    def test_update_current_request(self, make_controller) -> None:
        ctrl, _, _, _, _ = make_controller()
        ctrl.set_items([{"id": "tab-1", "method": "GET", "url": "/old"}])
        assert ctrl.update_current_request("POST", "/new") is True
        assert ctrl.items[0]["method"] == "POST"
        assert ctrl.items[0]["url"] == "/new"

    def test_update_no_change(self, make_controller) -> None:
        ctrl, _, _, _, _ = make_controller()
        ctrl.set_items([{"id": "tab-1", "method": "GET", "url": "/api"}])
        assert ctrl.update_current_request("GET", "/api") is False

    def test_rename_node_tabs_updates_matching_open_tab(self, make_controller) -> None:
        ctrl, _, save_calls, _, _ = make_controller()
        ctrl.set_items([
            {"id": "tab-1", "name": "Old", "nodeId": "node-1", "kind": "endpoint", "bodyText": "{}", "authType": "none"},
            {"id": "tab-2", "name": "Other", "nodeId": "node-2", "kind": "endpoint", "bodyText": "{}", "authType": "none"},
        ])
        assert ctrl.rename_node_tabs("node-1", "New") is True
        assert ctrl.items[0]["name"] == "New"
        assert ctrl.items[1]["name"] == "Other"
        assert save_calls[-1]["name"] == "New"

    def test_open_endpoint_creates_new_tab(self, make_controller) -> None:
        ctrl, _, save_calls, _, _ = make_controller()
        result = ctrl.open_endpoint("Users API", "GET", "/api/users", "node-1", [])
        assert result is True
        assert len(ctrl.items) == 1
        assert ctrl.items[0]["nodeId"] == "node-1"
        assert len(save_calls) == 1

    def test_open_endpoint_reuses_existing_tab(self, make_controller) -> None:
        ctrl, _, save_calls, _, _ = make_controller()
        ctrl.set_items([{"id": "tab-1", "name": "Existing", "nodeId": "node-1", "bodyText": "{}", "authType": "none"}])
        result = ctrl.open_endpoint("Users API", "GET", "/api/users", "node-1", [])
        assert result is False  # reused
        assert len(ctrl.items) == 1

    def test_open_endpoint_reuse_syncs_latest_tree_name(self, make_controller) -> None:
        ctrl, _, save_calls, _, _ = make_controller()
        ctrl.set_items([{
            "id": "tab-1",
            "name": "Old",
            "method": "GET",
            "url": "/old",
            "nodeId": "node-1",
            "bodyText": "{}",
            "authType": "none",
        }])
        result = ctrl.open_endpoint("New", "POST", "/new", "node-1", [])
        assert result is False
        assert ctrl.items[0]["name"] == "New"
        assert ctrl.items[0]["method"] == "POST"
        assert ctrl.items[0]["url"] == "/new"
        assert save_calls[-1]["name"] == "New"

    def test_close_current_removes_tab(self, make_controller) -> None:
        ctrl, _, _, _, delete_calls = make_controller()
        ctrl.set_items([
            {"id": "tab-1", "name": "A", "bodyText": "{}", "authType": "none"},
            {"id": "tab-2", "name": "B", "bodyText": "{}", "authType": "none"},
        ])
        ctrl.current_index = 0
        assert ctrl.close_current([]) is True
        assert len(ctrl.items) == 1
        assert len(delete_calls) == 1
        assert delete_calls[0] == "tab-1"
        assert ctrl.current_index == 0
        assert ctrl.items[0]["id"] == "tab-2"

    def test_close_last_tab(self, make_controller) -> None:
        ctrl, _, _, _, delete_calls = make_controller()
        ctrl.set_items([{"id": "tab-1", "name": "Only", "bodyText": "{}", "authType": "none"}])
        assert ctrl.close_current([]) is True
        assert ctrl.items == []
        assert ctrl.current_index == -1

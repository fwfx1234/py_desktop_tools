from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestApiTestServiceOrchestration:
    @pytest.fixture
    def service(self, api_database):
        from features.api_test.service import ApiTestService

        return ApiTestService(api_database.storage)

    def test_list_tabs_empty(self, service) -> None:
        assert service.list_tabs() == []

    def test_upsert_and_list_tabs(self, service, sample_tab_data) -> None:
        service.upsert_tab(
            sample_tab_data["id"], sample_tab_data["name"],
            sample_tab_data["method"], sample_tab_data["url"],
            sample_tab_data["requestMode"], sample_tab_data["bodyMode"],
            sample_tab_data["authType"], sample_tab_data["authValue"],
            sample_tab_data["headersText"], sample_tab_data["cookiesText"],
            sample_tab_data["bodyText"], sample_tab_data["paramsText"],
            sample_tab_data["pathParamsText"], sample_tab_data["envBaseUrl"],
            sample_tab_data["preOpsText"], sample_tab_data["postOpsText"],
            sample_tab_data["nodeId"], sample_tab_data["mockMode"],
        )
        tabs = service.list_tabs()
        assert len(tabs) == 1

    def test_delete_tab(self, service, sample_tab_data) -> None:
        service.upsert_tab(
            sample_tab_data["id"], sample_tab_data["name"],
            sample_tab_data["method"], sample_tab_data["url"],
            sample_tab_data["requestMode"], sample_tab_data["bodyMode"],
            sample_tab_data["authType"], sample_tab_data["authValue"],
            sample_tab_data["headersText"], sample_tab_data["cookiesText"],
            sample_tab_data["bodyText"], sample_tab_data["paramsText"],
            sample_tab_data["pathParamsText"], sample_tab_data["envBaseUrl"],
            sample_tab_data["preOpsText"], sample_tab_data["postOpsText"],
            sample_tab_data["nodeId"], sample_tab_data["mockMode"],
        )
        service.delete_tab("tab-001")
        assert service.list_tabs() == []

    def test_send_mock_mode(self, service) -> None:
        title, body, details = service.send_api(
            method="GET",
            url="/api/users",
            params_text="",
            headers_text="",
            body_text="",
            env_base_url="",
            auth_type="none",
            auth_value="",
            request_mode="mock",
            graphql_query="",
            graphql_variables="",
            global_params_text="",
            assertions_text="",
            mock_response_text='{"mock": true, "data": [1, 2, 3]}',
            tab_id="",
        )
        assert "MOCK" in title
        assert "mock" in body

    def test_send_mock_with_assertions(self, service) -> None:
        title, body, details = service.send_api(
            method="GET",
            url="/api/users",
            params_text="",
            headers_text="",
            body_text="",
            env_base_url="",
            auth_type="none",
            auth_value="",
            request_mode="mock",
            graphql_query="",
            graphql_variables="",
            global_params_text="",
            assertions_text="status == 200\nbody contains 'ok'",
            mock_response_text='{"ok": true}',
            tab_id="",
        )
        assert "--- Assertions ---" in body

    def test_send_mock_default_when_empty(self, service) -> None:
        title, body, details = service.send_api(
            method="POST",
            url="/api/items",
            params_text="",
            headers_text="",
            body_text="",
            env_base_url="",
            auth_type="none",
            auth_value="",
            request_mode="mock",
            graphql_query="",
            graphql_variables="",
            global_params_text="",
            assertions_text="",
            mock_response_text="",
            tab_id="",
        )
        assert "mock" in body.lower()

    def test_history_initial_state(self, service) -> None:
        history = service.get_history()
        assert history == []

    def test_websocket_mode_returns_request_details(self, service) -> None:
        title, body, details = service.send_api(
            method="GET",
            url="ws://echo.example.com",
            params_text="",
            headers_text="",
            body_text="",
            env_base_url="",
            auth_type="none",
            auth_value="",
            request_mode="websocket",
            graphql_query="",
            graphql_variables="",
            global_params_text="",
            assertions_text="",
            mock_response_text="",
            tab_id="",
        )
        assert "WS" in title

    def test_run_debug_cases(self, service) -> None:
        service.save_debug_case("GET /api/users", {
            "id": "case-1",
            "name": "Test Case",
            "method": "GET",
            "url": "/api/users",
            "requestMode": "mock",
            "mockMode": True,
            "bodyText": '{"ok": true}',
        })
        results = service.run_debug_cases("GET /api/users", ["case-1"])
        assert len(results) == 1
        assert results[0]["id"] == "case-1"

    def test_collection_tree_workflow(self, service) -> None:
        folder_id = service.create_collection_node(
            parent_id="", kind="folder", name="My API"
        )
        assert folder_id
        ep_id = service.create_collection_node(
            parent_id=folder_id, kind="endpoint", name="Get Users",
            method="GET", url="/api/users",
        )
        assert ep_id
        tree = service.load_collection_tree()
        assert len(tree) == 1
        assert tree[0]["name"] == "My API"
        assert len(tree[0]["children"]) == 1

    def test_environment_workflow(self, service) -> None:
        envs = [
            {"name": "Production", "baseUrl": "https://api.prod.example.com"},
            {"name": "Staging", "baseUrl": "https://api.staging.example.com"},
        ]
        service.save_environments(envs)
        result = service.list_environments()
        assert len(result) == 2

    def test_blank_env_base_url_uses_current_default_environment(self, service, sample_environment) -> None:
        service.save_environments([sample_environment])
        env = service._environment_for_base_url("")
        assert env["name"] == sample_environment["name"]
        assert env["baseUrl"] == sample_environment["baseUrl"]

    def test_collection_node_lifecycle(self, service) -> None:
        node_id = service.create_collection_node(
            parent_id="", kind="folder", name="Original"
        )
        service.rename_collection_node(node_id, "Renamed")
        service.set_collection_node_expanded(node_id, True)
        tree = service.load_collection_tree()
        assert tree[0]["name"] == "Renamed"
        assert tree[0]["expanded"] is True

    def test_set_all_nodes_expanded(self, service) -> None:
        service.create_collection_node(parent_id="", kind="folder", name="A")
        service.create_collection_node(parent_id="", kind="folder", name="B")
        service.set_all_collection_nodes_expanded(True)
        tree = service.load_collection_tree()
        assert all(n["expanded"] for n in tree)

    def test_move_node(self, service) -> None:
        f1 = service.create_collection_node(parent_id="", kind="folder", name="F1")
        f2 = service.create_collection_node(parent_id="", kind="folder", name="F2")
        ep = service.create_collection_node(
            parent_id=f1, kind="endpoint", name="EP", method="GET", url="/api"
        )
        service.move_collection_node(ep, f2)
        tree = service.load_collection_tree()
        assert len(tree[0]["children"]) == 0
        assert len(tree[1]["children"]) == 1

    def test_duplicate_node(self, service) -> None:
        node_id = service.create_collection_node(
            parent_id="", kind="folder", name="Template"
        )
        dup_id = service.duplicate_collection_node(node_id)
        assert dup_id
        tree = service.load_collection_tree()
        assert len(tree) == 2

    def test_delete_collection_node_cascading(self, service) -> None:
        folder_id = service.create_collection_node(
            parent_id="", kind="folder", name="ToDelete"
        )
        service.create_collection_node(
            parent_id=folder_id, kind="endpoint", name="Child", method="GET", url="/child"
        )
        service.delete_collection_node(folder_id)
        tree = service.load_collection_tree()
        assert tree == []

    def test_close_service_idempotent(self, service) -> None:
        service.close()
        service.close()

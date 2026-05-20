from __future__ import annotations

import pytest


class TestTabRepository:
    def test_empty_tabs_list(self, tab_repo) -> None:
        tabs = tab_repo.list_tabs()
        assert tabs == []

    def test_upsert_and_list_tab(self, tab_repo, sample_tab_data) -> None:
        tab_repo.upsert_tab(
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
        tabs = tab_repo.list_tabs()
        assert len(tabs) == 1
        assert tabs[0]["id"] == "tab-001"
        assert tabs[0]["method"] == "GET"
        assert tabs[0]["mockMode"] is False

    def test_upsert_updates_existing(self, tab_repo, sample_tab_data) -> None:
        tab_repo.upsert_tab(
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
        # Update with new method
        tab_repo.upsert_tab(
            "tab-001", "Updated Name", "POST", "/api/v2",
            "http", "JSON", "bearer", "tok", "h", "c", "b", "p",
            "pp", "http://env", "pre", "post", "node-2", True,
        )
        tabs = tab_repo.list_tabs()
        assert len(tabs) == 1
        assert tabs[0]["name"] == "Updated Name"
        assert tabs[0]["method"] == "POST"
        assert tabs[0]["mockMode"] is True

    def test_delete_tab(self, tab_repo, sample_tab_data) -> None:
        tab_repo.upsert_tab(
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
        tab_repo.delete_tab("tab-001")
        assert tab_repo.list_tabs() == []

    def test_history_recording(self, tab_repo) -> None:
        tab_repo.record_history(
            tab_id="tab-1", method="GET", url="/api/users",
            status=200, title="OK", response='{"data": []}',
        )
        history = tab_repo.list_history()
        assert len(history) >= 1
        assert history[0]["method"] == "GET"
        assert history[0]["status"] == 200

    def test_history_limit(self, tab_repo) -> None:
        for i in range(10):
            tab_repo.record_history(
                tab_id=f"tab-{i}", method="GET", url=f"/api/{i}",
                status=200, title="OK", response=f'{{"id": {i}}}',
            )
        result = tab_repo.list_history(limit=5)
        assert len(result) == 5

    def test_empty_history(self, tab_repo) -> None:
        assert tab_repo.list_history() == []

    def test_multiple_tabs_ordered_by_updated_at(self, tab_repo) -> None:
        tab_repo.upsert_tab(
            "tab-a", "A", "GET", "/a", "http", "none", "none", "",
            "", "", "", "", "", "", "", "", "", False,
        )
        import time
        time.sleep(0.002)  # ensure different timestamps
        tab_repo.upsert_tab(
            "tab-b", "B", "POST", "/b", "http", "none", "none", "",
            "", "", "", "", "", "", "", "", "", False,
        )
        tabs = tab_repo.list_tabs()
        assert len(tabs) == 2
        assert tabs[0]["id"] == "tab-b"  # most recently updated

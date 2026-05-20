from __future__ import annotations

import pytest


class TestDebugCaseService:
    def test_save_and_list_cases(self, case_service) -> None:
        case_service.save_case(
            case_id="case-1",
            endpoint_key="GET /api/users",
            payload={
                "name": "Should return 200",
                "method": "GET",
                "url": "/api/users",
                "requestMode": "http",
                "bodyMode": "none",
                "authType": "none",
                "authValue": "",
                "headersText": "",
                "cookiesText": "",
                "bodyText": "",
                "paramsText": "page: 1",
                "pathParamsText": "",
                "envBaseUrl": "http://localhost:8000",
                "preOpsText": "",
                "postOpsText": "status == 200",
                "mockMode": False,
            },
        )
        cases = case_service.list_cases("GET /api/users")
        assert len(cases) == 1
        assert cases[0]["id"] == "case-1"
        assert cases[0]["name"] == "Should return 200"
        assert cases[0]["paramsText"] == "page: 1"

    def test_update_existing_case(self, case_service) -> None:
        case_service.save_case(
            case_id="case-1",
            endpoint_key="GET /api/users",
            payload={"name": "Original", "method": "GET", "url": "/api/users"},
        )
        case_service.save_case(
            case_id="case-1",
            endpoint_key="GET /api/users",
            payload={"name": "Updated", "method": "POST", "url": "/api/v2"},
        )
        cases = case_service.list_cases("GET /api/users")
        assert len(cases) == 1
        assert cases[0]["name"] == "Updated"
        assert cases[0]["method"] == "POST"

    def test_list_cases_filtered_by_endpoint(self, case_service) -> None:
        case_service.save_case(
            case_id="case-1", endpoint_key="GET /users",
            payload={"name": "C1", "method": "GET", "url": "/users"},
        )
        case_service.save_case(
            case_id="case-2", endpoint_key="POST /items",
            payload={"name": "C2", "method": "POST", "url": "/items"},
        )
        assert len(case_service.list_cases("GET /users")) == 1
        assert len(case_service.list_cases("POST /items")) == 1
        assert len(case_service.list_cases("NONEXISTENT")) == 0

    def test_run_batch(self, case_service) -> None:
        case_service.save_case(
            case_id="case-1", endpoint_key="GET /users",
            payload={"name": "C1", "method": "GET", "url": "/users"},
        )
        case_service.save_case(
            case_id="case-2", endpoint_key="GET /users",
            payload={"name": "C2", "method": "POST", "url": "/users"},
        )

        call_log = []
        def sender(case):
            call_log.append(case)
            return (f"OK {case['method']}", f"body for {case['name']}", {"statusCode": "200"})

        results = case_service.run_batch("GET /users", ["case-1", "case-2"], sender)
        assert len(results) == 2
        assert len(call_log) == 2
        assert results[0]["id"] == "case-1"
        assert results[0]["title"] == "OK GET"

    def test_run_batch_with_missing_case_id(self, case_service) -> None:
        case_service.save_case(
            case_id="case-1", endpoint_key="GET /users",
            payload={"name": "C1", "method": "GET", "url": "/users"},
        )
        results = case_service.run_batch(
            "GET /users", ["case-1", "nonexistent"],
            lambda c: ("OK", "body", {}),
        )
        assert len(results) == 1

    def test_run_batch_empty_ids(self, case_service) -> None:
        assert case_service.run_batch("GET /users", [], lambda c: ("OK", "", {})) == []

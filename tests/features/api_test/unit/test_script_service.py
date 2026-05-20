from __future__ import annotations

import pytest

from features.api_test.script_service import RequestDraft, ScriptService


class TestApplyPreOps:
    @pytest.fixture
    def svc(self) -> ScriptService:
        return ScriptService()

    def test_empty_pre_ops(self, svc: ScriptService) -> None:
        draft = RequestDraft("GET", "/api", {}, {}, "")
        result, temp = svc.apply_pre_ops(draft, "")
        assert result.method == "GET"
        assert temp == {}

    def test_comment_lines_ignored(self, svc: ScriptService) -> None:
        draft = RequestDraft("GET", "/api", {}, {}, "")
        result, temp = svc.apply_pre_ops(draft, "# this is a comment\n# another")
        assert temp == {}

    def test_set_variable(self, svc: ScriptService) -> None:
        draft = RequestDraft("GET", "/api", {}, {}, "")
        result, temp = svc.apply_pre_ops(draft, "set token=abc123")
        assert temp == {"token": "abc123"}

    def test_set_multiple_variables(self, svc: ScriptService) -> None:
        draft = RequestDraft("GET", "/api", {}, {}, "")
        result, temp = svc.apply_pre_ops(
            draft, "set token=abc123\nset user_id=42"
        )
        assert temp == {"token": "abc123", "user_id": "42"}

    def test_header_operation(self, svc: ScriptService) -> None:
        draft = RequestDraft("GET", "/api", {}, {}, "")
        result, temp = svc.apply_pre_ops(draft, "header Authorization: Bearer token")
        assert result.headers == {"Authorization": "Bearer token"}

    def test_header_preserves_existing(self, svc: ScriptService) -> None:
        draft = RequestDraft("GET", "/api", {}, {"X-Custom": "old"}, "")
        result, temp = svc.apply_pre_ops(draft, "header X-Custom: new")
        assert result.headers == {"X-Custom": "new"}

    def test_query_operation(self, svc: ScriptService) -> None:
        draft = RequestDraft("GET", "/api", {}, {}, "")
        result, temp = svc.apply_pre_ops(draft, "query page=1")
        assert result.params == {"page": "1"}

    def test_query_preserves_existing(self, svc: ScriptService) -> None:
        draft = RequestDraft("GET", "/api", {"size": "10"}, {}, "")
        result, temp = svc.apply_pre_ops(draft, "query page=1")
        assert result.params == {"size": "10", "page": "1"}

    def test_body_append(self, svc: ScriptService) -> None:
        draft = RequestDraft("POST", "/api", {}, {}, '{"name": "Alice"')
        result, temp = svc.apply_pre_ops(draft, 'body.append , "age": 30}')
        assert result.body == '{"name": "Alice", "age": 30}'

    def test_multiple_operations_in_order(self, svc: ScriptService) -> None:
        draft = RequestDraft("GET", "/api", {}, {}, "")
        script = "set token=abc\nheader Authorization: Bearer {{token}}\nquery page=1"
        result, temp = svc.apply_pre_ops(draft, script)
        assert temp == {"token": "abc"}
        assert result.headers == {"Authorization": "Bearer {{token}}"}


class TestRunAssertions:
    @pytest.fixture
    def svc(self) -> ScriptService:
        return ScriptService()

    def test_empty_assertions(self, svc: ScriptService) -> None:
        result = svc.run_assertions(200, "{}", "")
        assert result == ""

    def test_status_assertion_pass(self, svc: ScriptService) -> None:
        result = svc.run_assertions(200, "{}", "status == 200")
        assert "PASS" in result

    def test_status_assertion_fail(self, svc: ScriptService) -> None:
        result = svc.run_assertions(404, "{}", "status == 200")
        assert "FAIL" in result

    def test_body_contains_pass(self, svc: ScriptService) -> None:
        result = svc.run_assertions(200, '{"ok": true}', "body contains 'ok'")
        assert "PASS" in result

    def test_body_contains_fail(self, svc: ScriptService) -> None:
        result = svc.run_assertions(200, '{"ok": true}', "body contains 'not_found'")
        assert "FAIL" in result

    def test_json_assertion_pass(self, svc: ScriptService) -> None:
        result = svc.run_assertions(200, '{"code": 200}', "json $.code == 200")
        assert "PASS" in result

    def test_json_assertion_fail(self, svc: ScriptService) -> None:
        result = svc.run_assertions(200, '{"code": 500}', "json $.code == 200")
        assert "FAIL" in result

    def test_non_json_body_with_json_assertion(self, svc: ScriptService) -> None:
        result = svc.run_assertions(200, "not json", "json $.code == 200")
        assert "FAIL" in result

    def test_unrecognized_assertion_is_skipped(self, svc: ScriptService) -> None:
        result = svc.run_assertions(200, "{}", "unknown command")
        assert "SKIP" in result

    def test_multiple_assertions(self, svc: ScriptService) -> None:
        script = "status == 200\nbody contains 'ok'\nunknown"
        result = svc.run_assertions(200, '{"ok": true}', script)
        lines = result.split("\n")
        assert len(lines) == 3
        assert "PASS" in lines[0]
        assert "PASS" in lines[1]
        assert "SKIP" in lines[2]


class TestExtractVariables:
    @pytest.fixture
    def svc(self) -> ScriptService:
        return ScriptService()

    def test_empty_post_ops(self, svc: ScriptService) -> None:
        result = svc.extract_variables('{"data": {"token": "abc"}}', "")
        assert result == {}

    def test_extract_simple_path(self, svc: ScriptService) -> None:
        result = svc.extract_variables(
            '{"data": {"token": "abc123"}}', "extract token=$.data.token"
        )
        assert result == {"token": "abc123"}

    def test_extract_nested_array(self, svc: ScriptService) -> None:
        result = svc.extract_variables(
            '{"items": [{"id": 1}, {"id": 2}]}', "extract first_id=$.items.0.id"
        )
        assert result == {"first_id": "1"}

    def test_extract_non_json_body(self, svc: ScriptService) -> None:
        result = svc.extract_variables("not json", "extract token=$.data.token")
        assert result == {}

    def test_extract_invalid_path(self, svc: ScriptService) -> None:
        result = svc.extract_variables(
            '{"data": {}}', "extract token=$.data.missing"
        )
        assert result == {}

    def test_extract_non_extract_lines_ignored(self, svc: ScriptService) -> None:
        result = svc.extract_variables(
            '{"data": {"token": "abc"}}', "# comment\nstatus == 200\nextract token=$.data.token"
        )
        assert result == {"token": "abc"}


class TestJsonPathGet:
    @pytest.fixture
    def svc(self) -> ScriptService:
        return ScriptService()

    def test_root_property(self, svc: ScriptService) -> None:
        assert svc._json_path_get({"name": "Alice"}, "$.name") == "Alice"

    def test_nested_property(self, svc: ScriptService) -> None:
        assert svc._json_path_get(
            {"data": {"user": {"name": "Alice"}}}, "$.data.user.name"
        ) == "Alice"

    def test_array_index(self, svc: ScriptService) -> None:
        assert svc._json_path_get(
            {"items": [{"id": 1}, {"id": 2}]}, "$.items.0.id"
        ) == 1

    def test_array_out_of_bounds(self, svc: ScriptService) -> None:
        assert svc._json_path_get(
            {"items": [{"id": 1}]}, "$.items.5.id"
        ) is None

    def test_path_not_starting_with_dollar(self, svc: ScriptService) -> None:
        assert svc._json_path_get({"key": "val"}, "key") is None

    def test_missing_dict_key(self, svc: ScriptService) -> None:
        assert svc._json_path_get({"a": 1}, "$.b") is None

    def test_non_index_on_array(self, svc: ScriptService) -> None:
        assert svc._json_path_get([1, 2, 3], "$.abc") is None

    def test_scalar_mid_path(self, svc: ScriptService) -> None:
        assert svc._json_path_get({"a": 42}, "$.a.b") is None

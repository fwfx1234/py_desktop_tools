from __future__ import annotations

from pathlib import Path
import re

import pytest

from features.api_test.variable_service import VariableService


class TestVariableResolution:
    @pytest.fixture
    def svc(self, tmp_path: Path) -> VariableService:
        from app.storage import SQLiteDatabase

        db = SQLiteDatabase(tmp_path / "var_test.db")
        svc = VariableService(db)
        svc.set_variable("global", "base_url", "https://api.example.com")
        svc.set_variable("environment", "token", "env_token_123", env_name="staging")
        svc.set_variable("module", "version", "v2")
        return svc

    def test_no_template_returns_unchanged(self, svc: VariableService) -> None:
        assert svc.resolve_text("plain text") == "plain text"

    def test_empty_text(self, svc: VariableService) -> None:
        assert svc.resolve_text("") == ""

    def test_resolve_global_variable(self, svc: VariableService) -> None:
        result = svc.resolve_text("{{base_url}}/api/users")
        assert result == "https://api.example.com/api/users"

    def test_resolve_with_spaces_in_template(self, svc: VariableService) -> None:
        result = svc.resolve_text("{{ base_url }}/api")
        assert result == "https://api.example.com/api"

    def test_unknown_variable_kept_literal(self, svc: VariableService) -> None:
        result = svc.resolve_text("{{unknown_var}}")
        assert result == "{{unknown_var}}"

    def test_temporary_variable_has_highest_priority(self, svc: VariableService) -> None:
        result = svc.resolve_text("{{base_url}}", temporary={"base_url": "temp_value"})
        assert result == "temp_value"

    def test_env_vars_before_module_vars(self, svc: VariableService) -> None:
        svc.set_variable("module", "key1", "module_value")
        result = svc.resolve_text("{{key1}}", env_vars={"key1": "env_value"})
        assert result == "env_value"

    def test_module_vars_before_global_vars(self, svc: VariableService) -> None:
        svc.set_variable("module", "key2", "module_value")
        result = svc.resolve_text("{{key2}}", module_vars={"key2": "override_module"})
        assert result == "override_module"

    def test_environment_scoped_variable(self, svc: VariableService) -> None:
        result = svc.resolve_text("{{token}}", env_name="staging")
        assert result == "env_token_123"

    def test_multiple_variables_in_one_text(self, svc: VariableService) -> None:
        result = svc.resolve_text("{{base_url}}/{{version}}/users")
        assert result == "https://api.example.com/v2/users"

    def test_variable_with_dots_and_dashes(self, svc: VariableService) -> None:
        svc.set_variable("global", "api.version", "v3")
        svc.set_variable("global", "x-custom-header", "my-value")
        assert svc.resolve_text("{{api.version}}") == "v3"
        assert svc.resolve_text("{{x-custom-header}}") == "my-value"

    def test_resolution_precedence_order(self, svc: VariableService) -> None:
        svc.set_variable("global", "key", "global")
        svc.set_variable("environment", "key", "env_store", env_name="staging")
        result = svc.resolve_text(
            "{{key}}",
            env_name="staging",
            temporary={"key": "temp"},
            env_vars={"key": "env_vars"},
            module_vars={"key": "module_vars"},
        )
        assert result == "temp"

    def test_magic_parameters(self, svc: VariableService) -> None:
        result = svc.resolve_text("{{$timestamp}} {{$timestamp_ms}} {{$iso_datetime}} {{$date}} {{$uuid}}")
        timestamp, timestamp_ms, iso_datetime, date_text, uuid_text = result.split()
        assert timestamp.isdigit()
        assert timestamp_ms.isdigit()
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", iso_datetime)
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", date_text)
        assert re.match(r"^[0-9a-f-]{36}$", uuid_text)

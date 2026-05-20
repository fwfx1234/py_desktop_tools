from __future__ import annotations

import pytest


class TestVariablePersistence:
    def test_set_and_resolve_global(self, variable_service) -> None:
        variable_service.set_variable("global", "base_url", "https://api.example.com")
        result = variable_service.resolve_text("{{base_url}}/users")
        assert result == "https://api.example.com/users"

    def test_overwrite_variable(self, variable_service) -> None:
        variable_service.set_variable("global", "key", "v1")
        variable_service.set_variable("global", "key", "v2")
        result = variable_service.resolve_text("{{key}}")
        assert result == "v2"

    def test_environment_scoped_isolation(self, variable_service) -> None:
        variable_service.set_variable("environment", "token", "prod_token", env_name="prod")
        variable_service.set_variable("environment", "token", "staging_token", env_name="staging")
        assert variable_service.resolve_text("{{token}}", env_name="prod") == "prod_token"
        assert variable_service.resolve_text("{{token}}", env_name="staging") == "staging_token"
        # No env_name — no match
        assert variable_service.resolve_text("{{token}}") == "{{token}}"

    def test_empty_key_is_noop(self, variable_service) -> None:
        variable_service.set_variable("global", "  ", "value")
        result = variable_service.resolve_text("{{  }}")
        assert result == "{{  }}"

    def test_multiple_scopes(self, variable_service) -> None:
        variable_service.set_variable("global", "g", "global_val")
        variable_service.set_variable("module", "g", "module_val")
        variable_service.set_variable("environment", "g", "env_val", env_name="staging")
        # env scoped: should match env store
        result = variable_service.resolve_text("{{g}}", env_name="staging")
        assert result == "env_val"
        # no env: should match module store
        result = variable_service.resolve_text("{{g}}")
        assert result == "module_val"

    def test_resolve_with_all_inputs(self, variable_service) -> None:
        variable_service.set_variable("global", "base", "http://global")
        result = variable_service.resolve_text(
            "{{base}}/{{token}}",
            env_name="staging",
            temporary={"token": "temp_token"},
        )
        assert result == "http://global/temp_token"

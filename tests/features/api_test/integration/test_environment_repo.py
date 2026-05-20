from __future__ import annotations

import pytest


class TestEnvironmentRepository:
    def test_list_returns_default_when_empty(self, environment_repo) -> None:
        envs = environment_repo.list_environments()
        assert len(envs) == 1
        assert envs[0]["name"] == "默认环境"

    def test_save_and_list_environments(self, environment_repo) -> None:
        envs_to_save = [
            {
                "id": "env-1",
                "name": "Production",
                "baseUrl": "https://api.prod.example.com",
                "variables": [
                    {"enabled": True, "key": "token", "value": "prod-token"},
                    {"enabled": False, "key": "debug", "value": "false"},
                ],
                "headers": [
                    {"enabled": True, "key": "X-Env", "value": "prod"},
                ],
            },
            {
                "id": "env-2",
                "name": "Staging",
                "baseUrl": "https://api.staging.example.com",
                "variables": [],
                "headers": [],
            },
        ]
        environment_repo.save_environments(envs_to_save)

        result = environment_repo.list_environments()
        assert len(result) == 2
        assert result[0]["name"] == "Production"
        assert result[0]["baseUrl"] == "https://api.prod.example.com"
        assert len(result[0]["variables"]) == 2
        assert result[0]["variables"][0]["key"] == "token"
        assert result[0]["variables"][0]["value"] == "prod-token"
        assert len(result[0]["headers"]) == 1

    def test_save_overwrites_existing(self, environment_repo) -> None:
        environment_repo.save_environments([
            {"name": "First", "baseUrl": "http://first.example.com"}
        ])
        environment_repo.save_environments([
            {"name": "Second", "baseUrl": "http://second.example.com"}
        ])
        result = environment_repo.list_environments()
        assert len(result) == 1
        assert result[0]["name"] == "Second"

    def test_save_empty_list_returns_default(self, environment_repo) -> None:
        environment_repo.save_environments([
            {"name": "Custom", "baseUrl": "http://custom.example.com"}
        ])
        environment_repo.save_environments([])
        result = environment_repo.list_environments()
        assert len(result) == 1
        assert result[0]["name"] == "默认环境"

    def test_empty_environment_name_is_preserved(self, environment_repo) -> None:
        environment_repo.save_environments([
            {"name": "", "baseUrl": "http://blank-name.example.com"}
        ])
        result = environment_repo.list_environments()
        assert len(result) == 1
        assert result[0]["name"] == ""

    def test_disabled_variables_not_filtered_in_storage(self, environment_repo) -> None:
        environment_repo.save_environments([
            {
                "name": "Env",
                "baseUrl": "http://example.com",
                "variables": [
                    {"enabled": False, "key": "secret", "value": "hidden"},
                ],
            }
        ])
        result = environment_repo.list_environments()
        assert len(result[0]["variables"]) == 1
        assert result[0]["variables"][0]["enabled"] is False

    def test_empty_key_with_value_is_kept(self, environment_repo) -> None:
        environment_repo.save_environments([
            {
                "name": "Env",
                "baseUrl": "http://example.com",
                "variables": [
                    {"enabled": True, "key": "", "value": "no-key"},
                    {"enabled": True, "key": "valid", "value": "yes"},
                ],
            }
        ])
        result = environment_repo.list_environments()
        # Rows with key="" but value present are kept (stored as-is)
        assert len(result[0]["variables"]) == 2

from __future__ import annotations

import json
from pathlib import Path

import pytest

from features.api_test.service import ApiTestService


class TestOpenApiImport:
    def test_parse_json_spec(self, tmp_path: Path) -> None:
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "servers": [
                {"url": "https://api.example.com", "description": "Production"},
                {"url": "https://staging.example.com", "description": "Staging"},
            ],
            "paths": {
                "/users": {
                    "get": {"summary": "List users", "operationId": "listUsers"},
                    "post": {"summary": "Create user", "operationId": "createUser"},
                },
                "/users/{id}": {
                    "get": {"summary": "Get user by ID"},
                    "delete": {"operationId": "deleteUser"},
                },
            },
        }
        spec_file = tmp_path / "openapi.json"
        spec_file.write_text(json.dumps(spec), encoding="utf-8")

        items, environments = ApiTestService.import_openapi(None, str(spec_file))

        assert len(items) == 4
        assert items[0]["method"] == "GET"
        assert items[0]["path"] == "/users"
        assert items[0]["summary"] == "List users"
        assert items[1]["method"] == "POST"
        assert items[2]["method"] == "GET"
        assert items[2]["path"] == "/users/{id}"
        assert items[3]["method"] == "DELETE"

        assert len(environments) == 2
        assert environments[0]["name"] == "Production"
        assert environments[0]["baseUrl"] == "https://api.example.com"
        assert environments[1]["name"] == "Staging"

    def test_parse_yaml_spec(self, tmp_path: Path) -> None:
        yaml_content = """openapi: "3.0.0"
info:
  title: Test API
  version: "1.0.0"
servers:
  - url: https://api.example.com
    description: Production
paths:
  /items:
    get:
      summary: List items
    post:
      summary: Create item
"""
        spec_file = tmp_path / "openapi.yaml"
        spec_file.write_text(yaml_content, encoding="utf-8")

        items, environments = ApiTestService.import_openapi(None, str(spec_file))

        assert len(items) == 2
        assert items[0]["method"] == "GET"
        assert items[0]["path"] == "/items"

    def test_empty_paths(self, tmp_path: Path) -> None:
        spec = {"openapi": "3.0.0", "paths": {}}
        spec_file = tmp_path / "empty.json"
        spec_file.write_text(json.dumps(spec), encoding="utf-8")

        items, environments = ApiTestService.import_openapi(None, str(spec_file))
        assert items == []

    def test_no_servers(self, tmp_path: Path) -> None:
        spec = {
            "openapi": "3.0.0",
            "paths": {"/users": {"get": {"summary": "List users"}}},
        }
        spec_file = tmp_path / "no_servers.json"
        spec_file.write_text(json.dumps(spec), encoding="utf-8")

        items, environments = ApiTestService.import_openapi(None, str(spec_file))
        assert len(items) == 1
        assert environments == []

    def test_skips_non_method_keys_in_paths(self, tmp_path: Path) -> None:
        spec = {
            "openapi": "3.0.0",
            "paths": {
                "/users": {
                    "get": {"summary": "List"},
                    "parameters": [{"name": "page", "in": "query"}],
                    "description": "User endpoints",
                }
            },
        }
        spec_file = tmp_path / "with_parameters.json"
        spec_file.write_text(json.dumps(spec), encoding="utf-8")

        items, _ = ApiTestService.import_openapi(None, str(spec_file))
        assert len(items) == 1

    def test_uses_operationid_fallback(self, tmp_path: Path) -> None:
        spec = {
            "openapi": "3.0.0",
            "paths": {
                "/health": {"get": {"operationId": "healthCheck"}}
            },
        }
        spec_file = tmp_path / "fallback.json"
        spec_file.write_text(json.dumps(spec), encoding="utf-8")

        items, _ = ApiTestService.import_openapi(None, str(spec_file))
        assert items[0]["summary"] == "healthCheck"

    def test_fallback_to_path_when_no_summary(self, tmp_path: Path) -> None:
        spec = {
            "openapi": "3.0.0",
            "paths": {
                "/health": {"get": {}}
            },
        }
        spec_file = tmp_path / "no_summary.json"
        spec_file.write_text(json.dumps(spec), encoding="utf-8")

        items, _ = ApiTestService.import_openapi(None, str(spec_file))
        assert items[0]["summary"] == "/health"

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.storage import SQLiteDatabase


# ---------------------------------------------------------------------------
# database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "api_test.db"


@pytest.fixture
def sqlite_database(tmp_db_path: Path) -> SQLiteDatabase:
    db = SQLiteDatabase(tmp_db_path)
    return db


@pytest.fixture
def api_database(sqlite_database: SQLiteDatabase):
    from features.api_test.db import ApiDatabase

    return ApiDatabase(sqlite_database)


# ---------------------------------------------------------------------------
# repository fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def collection_repo(api_database):
    from features.api_test.repositories.collection_repo import CollectionRepository

    return CollectionRepository(api_database.storage)


@pytest.fixture
def environment_repo(api_database):
    from features.api_test.repositories.environment_repo import EnvironmentRepository

    return EnvironmentRepository(api_database.storage)


@pytest.fixture
def tab_repo(api_database):
    from features.api_test.repositories.tab_repo import TabRepository

    return TabRepository(api_database.storage)


# ---------------------------------------------------------------------------
# service fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def variable_service(api_database):
    from features.api_test.variable_service import VariableService

    return VariableService(api_database.storage)


@pytest.fixture
def script_service():
    from features.api_test.script_service import ScriptService

    return ScriptService()


@pytest.fixture
def case_service(api_database):
    from features.api_test.case_service import DebugCaseService

    return DebugCaseService(api_database.storage)


# ---------------------------------------------------------------------------
# reusable test data
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_environment() -> dict[str, Any]:
    return {
        "id": "env-1",
        "name": "测试环境",
        "baseUrl": "http://127.0.0.1:8000",
        "variables": [
            {"enabled": True, "key": "token", "value": "abc123"},
            {"enabled": True, "key": "version", "value": "v1"},
            {"enabled": False, "key": "disabled_key", "value": "should_not_appear"},
        ],
        "headers": [
            {"enabled": True, "key": "X-Custom", "value": "custom-value"},
        ],
    }


@pytest.fixture
def sample_collection_tree() -> list[dict[str, Any]]:
    return [
        {
            "id": "folder-1",
            "parentId": "",
            "kind": "folder",
            "name": "用户模块",
            "expanded": True,
            "children": [
                {
                    "id": "ep-1",
                    "parentId": "folder-1",
                    "kind": "endpoint",
                    "name": "获取用户列表",
                    "method": "GET",
                    "path": "/api/users",
                    "expanded": False,
                    "children": [],
                },
                {
                    "id": "ep-2",
                    "parentId": "folder-1",
                    "kind": "endpoint",
                    "name": "创建用户",
                    "method": "POST",
                    "path": "/api/users",
                    "expanded": False,
                    "children": [],
                },
            ],
        },
    ]


@pytest.fixture
def sample_tab_data() -> dict[str, Any]:
    return {
        "id": "tab-001",
        "name": "GET /api/users",
        "method": "GET",
        "url": "/api/users",
        "requestMode": "http",
        "bodyMode": "none",
        "authType": "none",
        "authValue": "",
        "headersText": "Content-Type: application/json",
        "cookiesText": "",
        "bodyText": "",
        "paramsText": "",
        "pathParamsText": "",
        "envBaseUrl": "http://127.0.0.1:8000",
        "preOpsText": "",
        "postOpsText": "",
        "nodeId": "ep-1",
        "mockMode": False,
    }

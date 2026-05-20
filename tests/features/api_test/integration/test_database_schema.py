from __future__ import annotations

import pytest


class TestDatabaseSchema:
    def test_schema_creates_all_tables(self, api_database) -> None:
        with api_database.connect() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        table_names = {row[0] for row in tables}
        expected = {
            "http_tabs", "http_history",
            "api_collection_nodes", "api_environments",
            "api_environment_variables", "api_environment_headers",
            "debug_cases", "ws_sessions", "ws_messages", "api_variables",
        }
        assert expected.issubset(table_names)

    def test_schema_version(self, api_database) -> None:
        with api_database.connect() as conn:
            row = conn.execute("PRAGMA user_version").fetchone()
        assert row[0] == api_database.SCHEMA_VERSION

    def test_default_environment_seeded(self, api_database) -> None:
        with api_database.connect() as conn:
            row = conn.execute("SELECT id, name, base_url FROM api_environments LIMIT 1").fetchone()
        assert row is not None
        assert row[1] == "默认环境"

    def test_seed_is_idempotent(self, api_database) -> None:
        with api_database.connect() as conn:
            conn.execute("INSERT OR IGNORE INTO api_environments (id, name, base_url, sort_order, created_at, updated_at) VALUES ('test', 'Test', '', 1, 0, 0)")
        # Re-call ensure_schema — should not duplicate the default
        api_database.ensure_schema()
        with api_database.connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM api_environments").fetchone()[0]
        assert count == 2  # default + our inserted

    def test_foreign_keys_enabled(self, api_database) -> None:
        with api_database.connect() as conn:
            row = conn.execute("PRAGMA foreign_keys").fetchone()
        assert row[0] == 1

    def test_collection_node_kind_constraint(self, api_database) -> None:
        import sqlite3

        with api_database.connect() as conn:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO api_collection_nodes (id, parent_id, kind, name, sort_order, expanded, created_at, updated_at) "
                    "VALUES ('bad', '', 'invalid_kind', 'Bad', 0, 0, 0, 0)"
                )

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.storage import SQLiteDatabase, sqlite_database


def compute_pinyin(text: str) -> tuple[str, str]:
    try:
        from pypinyin import lazy_pinyin

        parts = lazy_pinyin(text)
        return "".join(parts).lower(), "".join(part[0] for part in parts).lower()
    except Exception:
        lowered = text.lower()
        return lowered, lowered


class CommandIndexDb:
    """Fresh command index for usage ranking and application cache."""

    def __init__(
        self,
        database: SQLiteDatabase | Path | None = None,
        *,
        db_path: Path | None = None,
    ) -> None:
        if database is None and db_path is not None:
            database = db_path
        if isinstance(database, SQLiteDatabase):
            self._database = database
        else:
            self._database = sqlite_database(
                database or "command_index.db",
                wal=True,
                check_same_thread=False,
            )
        self._db_path = self._database.path
        self._icon_dir = self._db_path.parent / "app_icons"
        self._icon_dir.mkdir(parents=True, exist_ok=True)
        self._db = self._database.open(check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS command_usage (
                command_key TEXT PRIMARY KEY,
                use_count INTEGER NOT NULL DEFAULT 0,
                last_used_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS app_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL,
                launch_path TEXT NOT NULL,
                bundle_id TEXT NOT NULL DEFAULT '',
                icon_path TEXT NOT NULL DEFAULT '',
                pinyin TEXT NOT NULL DEFAULT '',
                pinyin_initials TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                UNIQUE(platform, launch_path)
            )
            """
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_app_name ON app_entries(name, pinyin_initials)"
        )
        self._migrate_legacy_app_entries()
        self._db.commit()

    def _migrate_legacy_app_entries(self) -> None:
        rows = self._db.execute("PRAGMA table_info(app_entries)").fetchall()
        columns = {str(row[1]) for row in rows}
        if "launch_path" in columns and "platform" in columns and "bundle_id" in columns:
            return

        if "lnk_path" not in columns:
            return

        self._db.execute("ALTER TABLE app_entries RENAME TO app_entries_legacy")
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS app_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL,
                launch_path TEXT NOT NULL,
                bundle_id TEXT NOT NULL DEFAULT '',
                icon_path TEXT NOT NULL DEFAULT '',
                pinyin TEXT NOT NULL DEFAULT '',
                pinyin_initials TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                UNIQUE(platform, launch_path)
            )
            """
        )
        self._db.execute(
            """
            INSERT INTO app_entries (
                platform,
                name,
                launch_path,
                bundle_id,
                icon_path,
                pinyin,
                pinyin_initials,
                updated_at
            )
            SELECT
                'windows',
                name,
                lnk_path,
                '',
                icon_path,
                pinyin,
                pinyin_initials,
                updated_at
            FROM app_entries_legacy
            """
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_app_name ON app_entries(name, pinyin_initials)"
        )

    def close(self) -> None:
        self._db.close()

    def usage_map(self) -> dict[str, tuple[int, str]]:
        rows = self._db.execute(
            "SELECT command_key, use_count, last_used_at FROM command_usage"
        ).fetchall()
        return {row[0]: (row[1], row[2]) for row in rows}

    def record_launch(self, command_key: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            """
            INSERT INTO command_usage (command_key, use_count, last_used_at)
            VALUES (?, 1, ?)
            ON CONFLICT(command_key) DO UPDATE SET
                use_count = use_count + 1,
                last_used_at = excluded.last_used_at
            """,
            (command_key, now),
        )
        self._db.commit()

    def sync_apps(self, app_list: list[dict]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        count = 0
        for app in app_list:
            name = app["name"]
            pinyin, initials = compute_pinyin(name)
            self._db.execute(
                """
                INSERT INTO app_entries
                    (platform, name, launch_path, bundle_id, icon_path, pinyin, pinyin_initials, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(platform, launch_path) DO UPDATE SET
                    name = excluded.name,
                    bundle_id = excluded.bundle_id,
                    icon_path = excluded.icon_path,
                    pinyin = excluded.pinyin,
                    pinyin_initials = excluded.pinyin_initials,
                    updated_at = excluded.updated_at
                """,
                (
                    str(app.get("platform") or ""),
                    name,
                    str(app["launch_path"]),
                    str(app.get("bundle_id") or ""),
                    str(app.get("icon_path") or ""),
                    pinyin,
                    initials,
                    now,
                ),
            )
            count += 1
        self._db.execute("DELETE FROM app_entries WHERE updated_at != ?", (now,))
        self._db.commit()
        return count

    def get_apps(self) -> list[dict]:
        rows = self._db.execute(
            """
            SELECT id, platform, name, launch_path, bundle_id, icon_path, pinyin_initials
            FROM app_entries
            ORDER BY name
            """
        ).fetchall()
        return [self._app_row_to_dict(row) for row in rows]

    def search_apps(self, query: str, limit: int = 50) -> list[dict]:
        q = query.strip()
        if not q:
            rows = self._db.execute(
                """
                SELECT id, platform, name, launch_path, bundle_id, icon_path, pinyin_initials
                FROM app_entries
                ORDER BY name
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        else:
            like = f"%{q}%"
            rows = self._db.execute(
                """
                SELECT id, platform, name, launch_path, bundle_id, icon_path, pinyin_initials
                FROM app_entries
                WHERE name LIKE ? OR pinyin LIKE ? OR pinyin_initials LIKE ?
                ORDER BY name
                LIMIT ?
                """,
                (like, like, like, limit),
            ).fetchall()
        return [self._app_row_to_dict(row) for row in rows]

    def count_apps(self) -> int:
        row = self._db.execute("SELECT COUNT(*) FROM app_entries").fetchone()
        return int(row[0]) if row else 0

    def count_apps_with_icons(self) -> int:
        row = self._db.execute(
            "SELECT COUNT(*) FROM app_entries WHERE icon_path != ''"
        ).fetchone()
        return int(row[0]) if row else 0

    def get_icon_dir(self) -> Path:
        return self._icon_dir

    def record_launch_by_lnk(self, lnk_path: str) -> None:
        self.record_launch(f"app:{lnk_path}")

    def record_launch_by_app_path(self, launch_path: str) -> None:
        self.record_launch(f"app:{launch_path}")

    @staticmethod
    def _app_row_to_dict(row: tuple) -> dict:
        return {
            "id": row[0],
            "platform": row[1],
            "name": row[2],
            "launchPath": row[3],
            "bundleId": row[4],
            "iconPath": row[5],
            "initials": row[6],
            "lnkPath": row[3],
        }

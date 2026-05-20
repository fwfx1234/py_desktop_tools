from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from threading import RLock

from app.storage import SQLiteDatabase


_APP_SELECT = """
SELECT id, platform, name, launch_path, bundle_id, icon_path, pinyin_initials, aliases, search_text
FROM app_entries
"""


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
        database: SQLiteDatabase,
    ) -> None:
        self._database = database
        self._db_path = self._database.path
        self._icon_dir = self._db_path.parent / "app_icons"
        self._icon_dir.mkdir(parents=True, exist_ok=True)
        self._db = self._database.open(check_same_thread=False)
        self._lock = RLock()
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
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
                    aliases TEXT NOT NULL DEFAULT '',
                    search_text TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL,
                    UNIQUE(platform, launch_path)
                )
                """
            )
            self._ensure_app_entries_columns()
            self._backfill_app_search_text()
            self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_app_name ON app_entries(name, pinyin_initials)"
            )
            self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_app_search_text ON app_entries(search_text)"
            )
            self._db.execute(
                """
                CREATE TABLE IF NOT EXISTS app_index_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._db.commit()

    def _ensure_app_entries_columns(self) -> None:
        rows = self._db.execute("PRAGMA table_info(app_entries)").fetchall()
        columns = {str(row[1]) for row in rows}
        additions = {
            "aliases": "aliases TEXT NOT NULL DEFAULT ''",
            "search_text": "search_text TEXT NOT NULL DEFAULT ''",
        }
        for name, definition in additions.items():
            if name not in columns:
                self._db.execute(f"ALTER TABLE app_entries ADD COLUMN {definition}")

    def _backfill_app_search_text(self) -> None:
        rows = self._db.execute(
            "SELECT id, name, aliases FROM app_entries WHERE search_text = ''"
        ).fetchall()
        for row in rows:
            name = str(row[1] or "")
            aliases = _normalize_aliases(row[2], name)
            pinyin, initials = compute_pinyin(name)
            self._db.execute(
                """
                UPDATE app_entries
                SET pinyin = ?, pinyin_initials = ?, aliases = ?, search_text = ?
                WHERE id = ?
                """,
                (
                    pinyin,
                    initials,
                    json.dumps(aliases, ensure_ascii=False),
                    _build_app_search_text(name, aliases),
                    row[0],
                ),
            )

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def usage_map(self) -> dict[str, tuple[int, str]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT command_key, use_count, last_used_at FROM command_usage"
            ).fetchall()
        return {row[0]: (row[1], row[2]) for row in rows}

    def record_launch(self, command_key: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
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
        with self._lock:
            for app in app_list:
                name = app["name"]
                aliases = _normalize_aliases(app.get("aliases", []), name)
                pinyin, initials = compute_pinyin(name)
                search_text = _build_app_search_text(name, aliases)
                self._db.execute(
                    """
                    INSERT INTO app_entries
                        (platform, name, launch_path, bundle_id, icon_path, pinyin, pinyin_initials, aliases, search_text, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(platform, launch_path) DO UPDATE SET
                        name = excluded.name,
                        bundle_id = excluded.bundle_id,
                        icon_path = CASE
                            WHEN excluded.icon_path != '' THEN excluded.icon_path
                            ELSE app_entries.icon_path
                        END,
                        pinyin = excluded.pinyin,
                        pinyin_initials = excluded.pinyin_initials,
                        aliases = excluded.aliases,
                        search_text = excluded.search_text,
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
                        json.dumps(aliases, ensure_ascii=False),
                        search_text,
                        now,
                    ),
                )
                count += 1
            self._db.execute("DELETE FROM app_entries WHERE updated_at != ?", (now,))
            self._db.commit()
        return count

    def get_apps(self) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                f"{_APP_SELECT} ORDER BY name"
            ).fetchall()
        return [self._app_row_to_dict(row) for row in rows]

    def search_apps(self, query: str, limit: int = 50) -> list[dict]:
        q = query.strip()
        with self._lock:
            if not q:
                rows = self._db.execute(
                    f"{_APP_SELECT} ORDER BY name LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                tokens = _search_query_tokens(q)
                if not tokens:
                    rows = []
                else:
                    where = " AND ".join("search_text LIKE ?" for _ in tokens)
                    rows = self._db.execute(
                        f"{_APP_SELECT} WHERE {where} ORDER BY name LIMIT ?",
                        [f"%{token}%" for token in tokens] + [limit],
                    ).fetchall()
        return [self._app_row_to_dict(row) for row in rows]

    def count_apps(self) -> int:
        with self._lock:
            row = self._db.execute("SELECT COUNT(*) FROM app_entries").fetchone()
        return int(row[0]) if row else 0

    def count_apps_with_icons(self) -> int:
        with self._lock:
            row = self._db.execute(
                "SELECT COUNT(*) FROM app_entries WHERE icon_path != ''"
            ).fetchone()
        return int(row[0]) if row else 0

    def get_icon_dir(self) -> Path:
        return self._icon_dir

    def get_app_index_meta(self, key: str) -> str:
        with self._lock:
            row = self._db.execute(
                "SELECT value FROM app_index_meta WHERE key = ?",
                (key,),
            ).fetchone()
        return str(row[0]) if row else ""

    def set_app_index_meta(self, key: str, value: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._db.execute(
                """
                INSERT INTO app_index_meta (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, value, now),
            )
            self._db.commit()

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
            "aliases": _decode_aliases(row[7]),
            "searchText": row[8],
        }


def _decode_aliases(value: object) -> list[str]:
    return _normalize_aliases(value, "")


def _normalize_aliases(value: object, name: str) -> list[str]:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            raw_values = parsed if isinstance(parsed, list) else [value]
        except Exception:
            raw_values = [value]
    elif isinstance(value, list | tuple | set):
        raw_values = list(value)
    else:
        raw_values = []
    seen = {name.casefold()} if name else set()
    out: list[str] = []
    for raw in raw_values:
        text = str(raw).strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            out.append(text)
    return out


def _build_app_search_text(name: str, aliases: list[str]) -> str:
    terms: list[str] = []
    for text in [name, *aliases]:
        terms.extend(_search_terms_for_text(text))
    return " ".join(_unique_terms(terms))


def _search_terms_for_text(text: str) -> list[str]:
    pinyin, initials = compute_pinyin(text)
    return [
        text,
        _compact_text(text),
        pinyin,
        _compact_text(pinyin),
        initials,
        _mixed_initials(text),
        _latin_initials(text),
    ]


def _search_query_tokens(query: str) -> list[str]:
    tokens: list[str] = []
    for raw in re.split(r"\s+", query.strip().lower()):
        compact = _compact_text(raw)
        tokens.append(compact or raw)
    return [token for token in tokens if token]


def _compact_text(text: str) -> str:
    return "".join(char for char in text.lower() if char.isalnum())


def _latin_initials(text: str) -> str:
    words = re.findall(r"[A-Z]+(?=[A-Z][a-z]|\b)|[A-Z]?[a-z]+|\d+", text)
    return "".join(word[0].lower() for word in words if word)


def _mixed_initials(text: str) -> str:
    out: list[str] = []
    latin: list[str] = []
    non_latin: list[str] = []

    def flush_latin() -> None:
        if latin:
            out.append("".join(latin))
            latin.clear()

    def flush_non_latin() -> None:
        if non_latin:
            _, initials = compute_pinyin("".join(non_latin))
            out.append(initials)
            non_latin.clear()

    for char in text:
        if char.isascii() and char.isalnum():
            flush_non_latin()
            latin.append(char.lower())
            continue
        if latin:
            flush_latin()
        if char.isalnum():
            non_latin.append(char)
        else:
            flush_non_latin()
    flush_latin()
    flush_non_latin()
    return "".join(out)


def _unique_terms(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = str(value).strip().lower()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out

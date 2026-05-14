from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Any


SQLiteConnection = sqlite3.Connection
SQLiteRow = sqlite3.Row


class SQLiteDatabase:
    def __init__(
        self,
        path: Path,
        *,
        foreign_keys: bool = True,
        wal: bool = False,
        row_factory: Callable[[sqlite3.Cursor, tuple[Any, ...]], Any] | None = None,
        check_same_thread: bool = True,
        timeout: float = 30.0,
    ) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._foreign_keys = foreign_keys
        self._wal = wal
        self._row_factory = row_factory
        self._check_same_thread = check_same_thread
        self._timeout = timeout

    def open(
        self,
        *,
        row_factory: Callable[[sqlite3.Cursor, tuple[Any, ...]], Any] | None = None,
        check_same_thread: bool | None = None,
    ) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.path),
            check_same_thread=self._check_same_thread
            if check_same_thread is None
            else check_same_thread,
            timeout=self._timeout,
        )
        effective_row_factory = self._row_factory if row_factory is None else row_factory
        if effective_row_factory is not None:
            conn.row_factory = effective_row_factory
        self._apply_pragmas(conn)
        return conn

    @contextmanager
    def connection(
        self,
        *,
        row_factory: Callable[[sqlite3.Cursor, tuple[Any, ...]], Any] | None = None,
    ) -> Iterator[sqlite3.Connection]:
        conn = self.open(row_factory=row_factory)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _apply_pragmas(self, conn: sqlite3.Connection) -> None:
        if self._foreign_keys:
            conn.execute("PRAGMA foreign_keys = ON")
        if self._wal:
            conn.execute("PRAGMA journal_mode=WAL")

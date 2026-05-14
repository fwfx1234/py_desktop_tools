from __future__ import annotations

from pathlib import Path
import re

from app.paths import data_dir

from .dict_store import JsonDictStore
from .sqlite import SQLiteDatabase


class StorageManager:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or data_dir()
        self.root.mkdir(parents=True, exist_ok=True)

    def database(
        self,
        name: str | Path,
        *,
        foreign_keys: bool = True,
        wal: bool = False,
        row_factory=None,
        check_same_thread: bool = True,
        timeout: float = 30.0,
    ) -> SQLiteDatabase:
        return SQLiteDatabase(
            self.path(name),
            foreign_keys=foreign_keys,
            wal=wal,
            row_factory=row_factory,
            check_same_thread=check_same_thread,
            timeout=timeout,
        )

    def dict_store(
        self,
        namespace: str | Path,
        defaults: dict | None = None,
    ) -> JsonDictStore:
        return JsonDictStore(self._dict_path(namespace), defaults=defaults)

    def path(self, name: str | Path) -> Path:
        path = Path(name)
        if path.is_absolute():
            return path
        return self.root / path

    def _dict_path(self, namespace: str | Path) -> Path:
        path = Path(namespace)
        if path.is_absolute():
            return path
        parts = [_safe_part(part) for part in path.parts if part not in {"", "."}]
        if not parts:
            parts = ["default"]
        return self.root / "stores" / Path(*parts).with_suffix(".json")


def storage_manager(root: Path | None = None) -> StorageManager:
    return StorageManager(root)


def sqlite_database(name: str | Path, **kwargs) -> SQLiteDatabase:
    return storage_manager().database(name, **kwargs)


def dict_store(
    namespace: str | Path,
    defaults: dict | None = None,
    *,
    root: Path | None = None,
) -> JsonDictStore:
    return storage_manager(root).dict_store(namespace, defaults=defaults)


def _safe_part(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value.strip())
    return text.strip("._") or "default"

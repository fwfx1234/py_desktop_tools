from __future__ import annotations

from collections.abc import Iterator
import json
from pathlib import Path
from threading import RLock
from typing import Any


class JsonDictStore:
    def __init__(self, path: Path, defaults: dict[str, Any] | None = None) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._loaded_from_existing_file = self.path.exists()
        self._existed = self._loaded_from_existing_file
        self._data = self._read()
        if defaults:
            changed = False
            for key, value in defaults.items():
                if key not in self._data:
                    self._data[key] = value
                    changed = True
            if changed or not self._existed:
                self._write()

    @property
    def existed(self) -> bool:
        return self._existed

    @property
    def loaded_from_existing_file(self) -> bool:
        return self._loaded_from_existing_file

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value
            self._write()

    def set_many(self, values: dict[str, Any]) -> None:
        with self._lock:
            self._data.update(values)
            self._write()

    def setdefault_many(self, values: dict[str, Any]) -> None:
        with self._lock:
            changed = False
            for key, value in values.items():
                if key not in self._data:
                    self._data[key] = value
                    changed = True
            if changed:
                self._write()

    def delete(self, key: str) -> None:
        with self._lock:
            if key in self._data:
                del self._data[key]
                self._write()

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._write()

    def replace(self, values: dict[str, Any]) -> None:
        with self._lock:
            self._data = dict(values)
            self._write()

    def all(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._data)

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._data.keys())

    def items(self) -> list[tuple[str, Any]]:
        with self._lock:
            return list(self._data.items())

    def __contains__(self, key: object) -> bool:
        with self._lock:
            return key in self._data

    def __getitem__(self, key: str) -> Any:
        with self._lock:
            return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __delitem__(self, key: str) -> None:
        self.delete(key)

    def __iter__(self) -> Iterator[str]:
        with self._lock:
            return iter(list(self._data))

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    def _write(self) -> None:
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tmp_path.replace(self.path)
        self._existed = True

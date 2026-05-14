from __future__ import annotations

from pathlib import Path
import re

from app.storage import JsonDictStore, SQLiteDatabase, StorageManager


class PlatformStorageFactory:
    def __init__(self, storage_manager: StorageManager) -> None:
        self._storage_manager = storage_manager

    def for_plugin(self, plugin_id: str) -> "PluginStorageApi":
        return PluginStorageApi(self._storage_manager, plugin_id)


class PluginStorageApi:
    def __init__(self, storage_manager: StorageManager, plugin_id: str) -> None:
        self._storage_manager = storage_manager
        self._plugin_id = _safe_plugin_id(plugin_id)
        self._plugin_root = self._storage_manager.root / "plugins" / self._plugin_id
        self._plugin_cache_root = self._storage_manager.root / "cache" / "plugins" / self._plugin_id
        self._plugin_root.mkdir(parents=True, exist_ok=True)
        self._plugin_cache_root.mkdir(parents=True, exist_ok=True)

    def path(self, name: str | Path) -> Path:
        return self._safe_join(self._plugin_root, name)

    def cache_path(self, name: str | Path) -> Path:
        return self._safe_join(self._plugin_cache_root, name)

    def dict_store(
        self,
        namespace: str = "settings",
        defaults: dict | None = None,
    ) -> JsonDictStore:
        namespace_path = Path(namespace)
        if namespace_path.suffix != ".json":
            namespace_path = namespace_path.with_suffix(".json")
        return JsonDictStore(
            self._safe_join(self._plugin_root / "stores", namespace_path),
            defaults=defaults,
        )

    def database(self, name: str = "plugin.db", **kwargs) -> SQLiteDatabase:
        return SQLiteDatabase(self.path(name), **kwargs)

    @property
    def root(self) -> Path:
        return self._plugin_root

    @property
    def cache_root(self) -> Path:
        return self._plugin_cache_root

    def _safe_join(self, root: Path, name: str | Path) -> Path:
        path = Path(name)
        if path.is_absolute():
            raise ValueError("插件存储路径不支持绝对路径")
        if ".." in path.parts:
            raise ValueError("插件存储路径不支持上级目录")
        candidate = root.joinpath(*[part for part in path.parts if part not in {"", "."}])
        resolved_root = root.resolve()
        candidate.parent.mkdir(parents=True, exist_ok=True)
        resolved_candidate = candidate.resolve()
        if resolved_candidate != resolved_root and resolved_root not in resolved_candidate.parents:
            raise ValueError("插件存储路径越界")
        return candidate


def _safe_plugin_id(plugin_id: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_.-]+", "_", plugin_id.strip())
    return value.strip("._") or "anonymous"

from __future__ import annotations

from typing import TypeVar


T = TypeVar("T")


class ServiceRegistry:
    def __init__(
        self,
        *,
        platform: object | None = None,
        storage: object | None = None,
        clipboard: object | None = None,
        plugin_importer: object | None = None,
        imported_plugin_root: object | None = None,
    ) -> None:
        self._platform = platform
        self._storage = storage
        self._clipboard = clipboard
        self._plugin_importer = plugin_importer
        self._imported_plugin_root = imported_plugin_root

    @property
    def platform(self) -> object | None:
        return self._platform

    @platform.setter
    def platform(self, value: object | None) -> None:
        self._platform = value

    @property
    def storage(self) -> object | None:
        return self._storage

    @storage.setter
    def storage(self, value: object | None) -> None:
        self._storage = value

    @property
    def clipboard(self) -> object | None:
        return self._clipboard

    @clipboard.setter
    def clipboard(self, value: object | None) -> None:
        self._clipboard = value

    @property
    def plugin_importer(self) -> object | None:
        return self._plugin_importer

    @plugin_importer.setter
    def plugin_importer(self, value: object | None) -> None:
        self._plugin_importer = value

    @property
    def imported_plugin_root(self) -> object | None:
        return self._imported_plugin_root

    @imported_plugin_root.setter
    def imported_plugin_root(self, value: object | None) -> None:
        self._imported_plugin_root = value

    def require(self, key: str) -> object:
        value = getattr(self, key, None)
        if value is None:
            raise RuntimeError(f"缺少必需服务: {key}")
        return value

    def require_platform(self) -> object:
        return self.require("platform")

    def require_storage(self) -> object:
        return self.require("storage")

    def get_typed(self, key: str, expected_type: type[T]) -> T | None:
        value = getattr(self, key, None)
        if value is None:
            return None
        if not isinstance(value, expected_type):
            raise TypeError(f"服务类型不匹配: {key}")
        return value

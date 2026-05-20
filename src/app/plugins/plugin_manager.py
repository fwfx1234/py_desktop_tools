from __future__ import annotations

import importlib
import importlib.util
from collections.abc import Iterable
from pathlib import Path
import sys
from threading import RLock
from types import ModuleType
from typing import Callable

from app.logging import get_logger
from app.plugins.manifest import PluginManifest
from app.plugins.runtime import PluginAction, PluginContext, PluginRuntime, PluginSession


RuntimeFactory = Callable[[], PluginRuntime]


class PluginManager:
    """Manifest-first plugin manager with lazy runtime loading."""

    def __init__(self, manifests: Iterable[PluginManifest]) -> None:
        self._manifests = {manifest.id: manifest for manifest in manifests}
        self._runtimes: dict[str, PluginRuntime] = {}
        self._lock = RLock()
        self._log = get_logger("app.plugins.plugin_manager")

    def all_manifests(self) -> list[PluginManifest]:
        return sorted(self._manifests.values(), key=lambda item: item.order)

    def get_manifest(self, plugin_id: str) -> PluginManifest | None:
        return self._manifests.get(plugin_id)

    def get_loaded_runtime(self, plugin_id: str) -> PluginRuntime | None:
        with self._lock:
            return self._runtimes.get(plugin_id)

    def ensure_runtime(self, plugin_id: str) -> PluginRuntime | None:
        manifest = self.get_manifest(plugin_id)
        if manifest is None:
            return None
        with self._lock:
            runtime = self._load_runtime(manifest)
        if runtime is not None:
            self._log.debug("plugin.runtime.ensure", "确保插件 runtime 存在", pluginId=plugin_id)
        return runtime

    def open_session(
        self,
        plugin_id: str,
        ctx: PluginContext,
        *,
        command_id: str = "",
        input_text: str = "",
        payload: dict | None = None,
        trace_id: str = "",
    ) -> PluginSession | None:
        manifest = self.get_manifest(plugin_id)
        if manifest is None:
            return None
        with self._lock:
            runtime = self._load_runtime(manifest)
        action = PluginAction(
            manifest=manifest,
            command_id=command_id or manifest.primary_command.id,
            input_text=input_text,
            payload=payload or {},
            trace_id=trace_id,
        )
        try:
            return runtime.on_enter(ctx, action)
        except Exception as exc:
            self._log.error(
                "plugin.runtime.on_enter_failed",
                "插件 on_enter 失败",
                pluginId=plugin_id,
                traceId=trace_id,
                commandId=action.command_id,
                error=str(exc),
            )
            return None

    def close_runtime(self, plugin_id: str) -> None:
        manifest = self.get_manifest(plugin_id)
        if manifest is not None and manifest.activation == "background":
            return
        with self._lock:
            runtime = self._runtimes.pop(plugin_id, None)
        if runtime is not None:
            runtime.on_exit()
            self._log.debug("plugin.runtime.close", "关闭插件 runtime", pluginId=plugin_id)

    def close_all(self) -> None:
        with self._lock:
            runtimes = list(self._runtimes.values())
            self._runtimes.clear()
        for runtime in runtimes:
            runtime.on_exit()

    def _load_runtime(self, manifest: PluginManifest) -> PluginRuntime:
        runtime = self._runtimes.get(manifest.id)
        if runtime is not None:
            return runtime

        module_name, factory_name = self._parse_entrypoint(manifest)
        try:
            module = self._import_module(manifest, module_name)
            factory: RuntimeFactory = getattr(module, factory_name)
            runtime = factory()
            self._runtimes[manifest.id] = runtime
            self._log.debug(
                "plugin.runtime.load",
                "加载插件 runtime",
                pluginId=manifest.id,
                module=module_name,
                factory=factory_name,
            )
            return runtime
        except Exception as exc:
            self._log.error(
                "plugin.runtime.load_failed",
                "加载插件 runtime 失败",
                pluginId=manifest.id,
                module=module_name,
                factory=factory_name,
                error=str(exc),
            )
            raise

    @staticmethod
    def _parse_entrypoint(manifest: PluginManifest) -> tuple[str, str]:
        module_name, separator, factory_name = manifest.entrypoint.partition(":")
        module_name = module_name.strip()
        factory_name = factory_name.strip()
        if not separator or not module_name or not factory_name:
            get_logger("app.plugins.plugin_manager").warning(
                "plugin.runtime.entrypoint_invalid",
                "插件 entrypoint 非法",
                pluginId=manifest.id,
                entrypoint=manifest.entrypoint,
            )
            raise ValueError(
                f"Invalid entrypoint for plugin {manifest.id}: {manifest.entrypoint!r}"
            )
        return module_name, factory_name

    @staticmethod
    def _import_module(manifest: PluginManifest, module_name: str):
        package_dir = manifest.package_dir
        if package_dir is None:
            return importlib.import_module(module_name)

        package_path = Path(package_dir)
        module_path = package_path.joinpath(*module_name.split(".")).with_suffix(".py")
        if not module_path.is_file():
            return importlib.import_module(module_name)

        package_name = f"_py_desktop_plugin_{_safe_module_part(manifest.id)}"
        _ensure_plugin_packages(package_name, package_path, module_name)
        import_name = f"{package_name}.{module_name}"
        loaded = sys.modules.get(import_name)
        if loaded is not None:
            return loaded

        spec = importlib.util.spec_from_file_location(import_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load plugin module: {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[import_name] = module
        inserted = False
        package_path_text = str(package_path)
        if package_path_text not in sys.path:
            sys.path.insert(0, package_path_text)
            inserted = True
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(import_name, None)
            raise
        finally:
            if inserted:
                try:
                    sys.path.remove(package_path_text)
                except ValueError:
                    pass
        return module


def _safe_module_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value)


def _ensure_plugin_packages(
    package_name: str,
    package_path: Path,
    module_name: str,
) -> None:
    """Create a synthetic package so plugin-local relative imports work."""

    _ensure_package_module(package_name, package_path)
    current_name = package_name
    current_path = package_path
    parts = module_name.split(".")[:-1]
    for part in parts:
        current_name = f"{current_name}.{part}"
        current_path = current_path / part
        _ensure_package_module(current_name, current_path)


def _ensure_package_module(package_name: str, package_path: Path) -> ModuleType:
    existing = sys.modules.get(package_name)
    if isinstance(existing, ModuleType):
        return existing
    module = ModuleType(package_name)
    module.__file__ = str(package_path / "__init__.py")
    module.__package__ = package_name
    module.__path__ = [str(package_path)]  # type: ignore[attr-defined]
    sys.modules[package_name] = module
    return module

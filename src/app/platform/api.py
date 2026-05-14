from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .models import AppEntry, PlatformInfo, PlatformResult, SystemCommand

if TYPE_CHECKING:
    from .services import PlatformServices


class PlatformApi:
    def __init__(self, services: "PlatformServices", *, plugin_id: str = "") -> None:
        self._services = services
        self._plugin_id = plugin_id

    @property
    def clipboard(self) -> object:
        return self._services.clipboard

    @property
    def dialogs(self) -> object:
        return self._services.dialogs

    @property
    def screen(self) -> object:
        return self._services.screen

    @property
    def storage(self) -> object:
        return self._services.storage_factory.for_plugin(self._effective_plugin_id())

    @property
    def commands(self) -> object:
        return self._services.dynamic_command_api_factory.for_plugin(self._effective_plugin_id())

    @property
    def permissions(self) -> object:
        return self._services.permissions

    @property
    def info(self) -> PlatformInfo:
        return self._services.info

    def for_plugin(self, plugin_id: str) -> "PlatformApi":
        return PlatformApi(self._services, plugin_id=plugin_id)

    def is_windows(self) -> bool:
        return self.info.name == "windows"

    def is_macos(self) -> bool:
        return self.info.name == "macos"

    def user_data_dir(self) -> Path:
        return self._services.paths.user_data_dir()

    def cache_dir(self) -> Path:
        return self._services.paths.cache_dir()

    def resource_root(self) -> Path:
        return self._services.paths.resource_root()

    def plugin_data_dir(self) -> Path:
        return self.storage.root

    def plugin_cache_dir(self) -> Path:
        return self.storage.cache_root

    def scan_applications(self) -> list[AppEntry]:
        icon_dir = self.cache_dir() / "app_icons"
        icon_dir.mkdir(parents=True, exist_ok=True)
        return self._services.app_indexer.scan_apps(icon_dir)

    def system_commands(self) -> list[SystemCommand]:
        return self._services.system_commands.commands()

    def open_path(self, path: str | Path) -> PlatformResult:
        return self._services.external_launcher.open_path(path)

    def reveal_in_file_manager(self, path: str | Path) -> PlatformResult:
        return self._services.external_launcher.reveal_in_file_manager(path)

    def open_url(self, url: str) -> PlatformResult:
        return self._services.external_launcher.open_url(url)

    def launch_application(self, app: AppEntry | dict) -> PlatformResult:
        return self._services.external_launcher.launch_app(app)

    def run_system_action(self, action: str) -> PlatformResult:
        allowed_actions = {command.action for command in self.system_commands()}
        if action not in allowed_actions:
            return PlatformResult(False, "系统动作不在允许列表中", "forbidden")
        return self._services.external_launcher.launch_system_action(action)

    def _effective_plugin_id(self) -> str:
        return self._plugin_id or "anonymous"

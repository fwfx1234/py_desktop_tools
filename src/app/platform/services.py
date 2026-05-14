from __future__ import annotations

from dataclasses import dataclass

from .api import PlatformApi
from .models import PlatformInfo


@dataclass(slots=True)
class PlatformServices:
    info: PlatformInfo
    default_launcher_hotkey: str
    default_clipboard_hotkey: str
    paths: object
    hotkey_factory: object
    app_indexer: object
    external_launcher: object
    system_commands: object
    clipboard: object
    dialogs: object
    screen: object
    storage_factory: object
    dynamic_command_api_factory: object
    permissions: object

    def create_api(self, *, plugin_id: str = "") -> PlatformApi:
        return PlatformApi(self, plugin_id=plugin_id)

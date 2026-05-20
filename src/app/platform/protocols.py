from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .models import AppEntry, PlatformResult


class AppIndexerProtocol(Protocol):
    def scan_apps(
        self,
        icon_dir: Path | None = None,
        *,
        extract_icons: bool = True,
    ) -> list[AppEntry]:
        ...

    def quick_signature(self) -> str:
        ...


class ClipboardApiProtocol(Protocol):
    def read_text(self) -> str:
        ...

    def write_text(self, text: str) -> PlatformResult:
        ...

    def write_files(self, paths: list[str | Path]) -> PlatformResult:
        ...

    def clear(self) -> PlatformResult:
        ...


class HotkeyManagerProtocol(Protocol):
    hotkeyPressed: object

    def register(self, hotkey: str | None = None) -> bool:
        ...

    def unregister(self) -> None:
        ...

    def is_registered(self) -> bool:
        ...


class HotkeyFactoryProtocol(Protocol):
    def create(self, *, parent: object | None, hotkey: str, hotkey_id: int) -> HotkeyManagerProtocol:
        ...

    def install_filter(self, app: object, manager: HotkeyManagerProtocol) -> object | None:
        ...


class ExternalLauncherProtocol(Protocol):
    def launch_app(self, app: AppEntry | dict) -> PlatformResult:
        ...

    def launch_system_action(self, action: str) -> PlatformResult:
        ...

    def open_path(self, path: str | Path) -> PlatformResult:
        ...

    def reveal_in_file_manager(self, path: str | Path) -> PlatformResult:
        ...

    def open_url(self, url: str) -> PlatformResult:
        ...


class SystemCommandProviderProtocol(Protocol):
    def commands(self) -> list:
        ...


class DialogApiProtocol(Protocol):
    def open_file(self, options: object | None = None) -> Path | None:
        ...

    def open_files(self, options: object | None = None) -> list[Path]:
        ...

    def save_file(self, options: object | None = None) -> Path | None:
        ...


class ScreenApiProtocol(Protocol):
    def primary_display(self) -> object | None:
        ...

    def all_displays(self) -> list:
        ...

    def cursor_position(self) -> object:
        ...

    def display_at_cursor(self) -> object | None:
        ...


class StorageFactoryProtocol(Protocol):
    def for_plugin(self, plugin_id: str) -> object:
        ...


class DynamicCommandApiFactoryProtocol(Protocol):
    def for_plugin(self, plugin_id: str) -> object:
        ...

    def set_registry(self, registry: object | None) -> None:
        ...


class PermissionApiProtocol(Protocol):
    def accessibility_status(self) -> PlatformResult:
        ...

    def open_accessibility_settings(self) -> PlatformResult:
        ...

    def screen_recording_status(self) -> PlatformResult:
        ...

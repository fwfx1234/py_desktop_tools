from __future__ import annotations

import platform
import sys

from app import paths as app_paths
from app.storage import StorageManager

from .apps_noop import NoopAppIndexer
from .clipboard import QtClipboardApi
from .dialogs import QtDialogApi
from .dynamic_commands import PlatformCommandApiFactory
from .hotkey_noop import NoopHotkeyFactory
from .models import PlatformInfo
from .permissions import DefaultPermissionApi
from .screen import QtScreenApi
from .services import PlatformServices
from .storage import PlatformStorageFactory
from .external_launcher import NoopExternalLauncher
from .system_commands import NoopSystemCommandProvider


def create_platform_services(app: object | None = None) -> PlatformServices:
    del app
    is_packaged = bool(getattr(sys, "frozen", False))
    version = platform.mac_ver()[0] if sys.platform == "darwin" else platform.version()

    if sys.platform == "win32":
        from .apps_windows import WindowsAppIndexer
        from .hotkey_windows import WindowsHotkeyFactory
        from .system_commands import WindowsSystemCommandProvider
        from .external_launcher import WindowsExternalLauncher

        return PlatformServices(
            info=PlatformInfo("windows", "Windows", version=version, is_packaged=is_packaged),
            default_launcher_hotkey="Alt+Space",
            default_clipboard_hotkey="Alt+V",
            paths=app_paths,
            hotkey_factory=WindowsHotkeyFactory(),
            app_indexer=WindowsAppIndexer(),
            external_launcher=WindowsExternalLauncher(),
            system_commands=WindowsSystemCommandProvider(),
            clipboard=QtClipboardApi(),
            dialogs=QtDialogApi(),
            screen=QtScreenApi(),
            storage_factory=PlatformStorageFactory(StorageManager()),
            dynamic_command_api_factory=PlatformCommandApiFactory(None),
            permissions=DefaultPermissionApi(),
        )
    if sys.platform == "darwin":
        from .apps_macos import MacOSAppIndexer
        from .hotkey_macos import MacHotkeyFactory
        from .system_commands import MacOSSystemCommandProvider
        from .external_launcher import MacOSExternalLauncher

        return PlatformServices(
            info=PlatformInfo("macos", "macOS", version=version, is_packaged=is_packaged),
            default_launcher_hotkey="Alt+Space",
            default_clipboard_hotkey="Alt+V",
            paths=app_paths,
            hotkey_factory=MacHotkeyFactory(),
            app_indexer=MacOSAppIndexer(),
            external_launcher=MacOSExternalLauncher(),
            system_commands=MacOSSystemCommandProvider(),
            clipboard=QtClipboardApi(),
            dialogs=QtDialogApi(),
            screen=QtScreenApi(),
            storage_factory=PlatformStorageFactory(StorageManager()),
            dynamic_command_api_factory=PlatformCommandApiFactory(None),
            permissions=DefaultPermissionApi(),
        )
    return PlatformServices(
        info=PlatformInfo("unknown", platform.system() or "Unknown", version=version, is_packaged=is_packaged),
        default_launcher_hotkey="Alt+Space",
        default_clipboard_hotkey="Alt+V",
        paths=app_paths,
        hotkey_factory=NoopHotkeyFactory(),
        app_indexer=NoopAppIndexer(),
        external_launcher=NoopExternalLauncher(),
        system_commands=NoopSystemCommandProvider(),
        clipboard=QtClipboardApi(),
        dialogs=QtDialogApi(),
        screen=QtScreenApi(),
        storage_factory=PlatformStorageFactory(StorageManager()),
        dynamic_command_api_factory=PlatformCommandApiFactory(None),
        permissions=DefaultPermissionApi(),
    )

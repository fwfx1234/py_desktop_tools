from __future__ import annotations

from app.plugins.runtime import SimpleQmlRuntime

from .view_model import SystemSettingsViewModel


def create_runtime() -> SimpleQmlRuntime:
    return SimpleQmlRuntime(
        lambda ctx: SystemSettingsViewModel(
            ctx.command_service,
            ctx.platform.permissions,
            ctx.services.plugin_importer,
            ctx.services.imported_plugin_root,
            ctx.platform,
            ctx.services.storage,
        )
    )

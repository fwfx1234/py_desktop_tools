from __future__ import annotations

from app.plugins.runtime import PluginContext, SimpleQmlRuntime
from app.storage import StorageManager

from .view_model import DownloadManagerViewModel


def _create_view_model(ctx: PluginContext) -> DownloadManagerViewModel:
    storage = ctx.services.storage
    database = storage.database("download_manager.db", check_same_thread=False) if isinstance(storage, StorageManager) else None
    return DownloadManagerViewModel(platform_api=ctx.platform, database=database)


def create_runtime() -> SimpleQmlRuntime:
    return SimpleQmlRuntime(_create_view_model)

from __future__ import annotations

from app.plugins.runtime import PluginContext, SimpleQmlRuntime
from app.storage import StorageManager

from .view_model import RemoteFilesViewModel


def _create_view_model(ctx: PluginContext) -> RemoteFilesViewModel:
    storage = ctx.services.storage
    if not isinstance(storage, StorageManager):
        raise RuntimeError("Storage manager is unavailable")
    return RemoteFilesViewModel(storage.database("remote_files.db", check_same_thread=False))


def create_runtime() -> SimpleQmlRuntime:
    return SimpleQmlRuntime(_create_view_model)

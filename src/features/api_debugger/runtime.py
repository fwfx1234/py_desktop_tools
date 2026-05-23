from __future__ import annotations

from app.plugins.runtime import PluginContext, SimpleQmlRuntime
from app.storage import StorageManager

from .view_model import ApiDebuggerViewModel


def _create_view_model(ctx: PluginContext) -> ApiDebuggerViewModel:
    storage = ctx.services.storage
    if not isinstance(storage, StorageManager):
        raise RuntimeError("Storage manager is unavailable")
    return ApiDebuggerViewModel(storage.database("api_debugger.db"))


def create_runtime() -> SimpleQmlRuntime:
    return SimpleQmlRuntime(_create_view_model)

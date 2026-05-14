from __future__ import annotations

from app.plugins.runtime import PluginContext, SimpleQmlRuntime
from app.storage import StorageManager

from .view_model import ApiTestViewModel


def _create_view_model(ctx: PluginContext) -> ApiTestViewModel:
    storage = ctx.services.get("storage")
    if isinstance(storage, StorageManager):
        return ApiTestViewModel(storage.database("api_test.db"))
    return ApiTestViewModel()


def create_runtime() -> SimpleQmlRuntime:
    return SimpleQmlRuntime(_create_view_model)

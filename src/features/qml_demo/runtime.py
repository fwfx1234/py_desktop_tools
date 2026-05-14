from __future__ import annotations

from app.plugins.runtime import SimpleQmlRuntime

from .view_model import QmlDemoViewModel


def create_runtime() -> SimpleQmlRuntime:
    return SimpleQmlRuntime(lambda _ctx: QmlDemoViewModel())

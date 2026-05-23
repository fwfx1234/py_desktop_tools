from __future__ import annotations

from app.plugins.runtime import SimpleQmlRuntime


def create_runtime() -> SimpleQmlRuntime:
    return SimpleQmlRuntime(lambda _ctx: None)

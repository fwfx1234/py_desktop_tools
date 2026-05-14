from __future__ import annotations

from app.plugins.runtime import SimpleQmlRuntime


def create_settings_runtime() -> SimpleQmlRuntime:
    return SimpleQmlRuntime(lambda _ctx: None)


def create_about_runtime() -> SimpleQmlRuntime:
    return SimpleQmlRuntime(lambda _ctx: None)

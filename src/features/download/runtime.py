from __future__ import annotations

from app.plugins.runtime import SimpleQmlRuntime

from .view_model import DownloadViewModel


def create_runtime() -> SimpleQmlRuntime:
    return SimpleQmlRuntime(lambda ctx: DownloadViewModel(platform_api=ctx.platform))

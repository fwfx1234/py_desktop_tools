from __future__ import annotations

from app.plugins.runtime import SimpleQmlRuntime

from .view_model import PacketCaptureViewModel


def create_runtime() -> SimpleQmlRuntime:
    return SimpleQmlRuntime(lambda ctx: PacketCaptureViewModel(platform_api=ctx.platform))

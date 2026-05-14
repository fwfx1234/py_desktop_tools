from __future__ import annotations

from app.plugins.runtime import PluginAction, PluginContext, QmlPluginSession

from .view_model import QrViewModel


class QrRuntime:
    def on_enter(self, ctx: PluginContext, action: PluginAction) -> QmlPluginSession:
        del ctx
        view_model = QrViewModel(action.input_text)
        return QrSession(action.manifest, view_model)

    def on_exit(self) -> None:
        return


class QrSession(QmlPluginSession):
    def __init__(self, manifest, view_model: QrViewModel) -> None:
        super().__init__(
            manifest=manifest,
            launch_mode=manifest.primary_command.launch_mode,
            view_model=view_model,
        )
        self._qr_view_model = view_model

    def on_input_changed(self, text: str) -> list[dict]:
        self._qr_view_model.setInputText(text)
        return []


def create_runtime() -> QrRuntime:
    return QrRuntime()

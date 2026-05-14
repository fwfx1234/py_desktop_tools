from __future__ import annotations

from app.plugins.runtime import PluginAction, PluginContext, QmlPluginSession
from app.storage import StorageManager

from .service import ClipboardBackgroundService, DEFAULT_CLIPBOARD_CONFIG
from .view_model import ClipboardWindowViewModel


SERVICE_KEY = "clipboard.background"


class ClipboardRuntime:
    """Resident clipboard listener plus lazy inline session factory."""

    def __init__(self) -> None:
        self._service: ClipboardBackgroundService | None = None

    def on_background_start(self, ctx: PluginContext) -> None:
        if self._service is not None:
            return
        storage = ctx.services.get("storage")
        if not isinstance(storage, StorageManager):
            storage = StorageManager()
            ctx.services["storage"] = storage
        self._service = ClipboardBackgroundService(
            storage.database(
                "clipboard.db",
                row_factory=None,
                check_same_thread=False,
            ),
            settings_store=storage.dict_store(
                "clipboard/settings",
                defaults=DEFAULT_CLIPBOARD_CONFIG,
            ),
        )
        ctx.services[SERVICE_KEY] = self._service

    def on_enter(self, ctx: PluginContext, action: PluginAction):
        service = self._service or ctx.services.get(SERVICE_KEY)
        if service is None:
            self.on_background_start(ctx)
            service = self._service
        if not isinstance(service, ClipboardBackgroundService):
            raise RuntimeError("Clipboard background service is unavailable")

        initial_panel = str(action.payload.get("panel") or "history")
        view_model = ClipboardWindowViewModel(
            service,
            initial_panel=initial_panel,
            initial_query=action.input_text,
        )
        return ClipboardInlineSession(
            manifest=action.manifest,
            view_model=view_model,
        )

    def on_background_stop(self) -> None:
        if self._service is not None:
            self._service.close()
            self._service = None

    def on_exit(self) -> None:
        return


def create_runtime() -> ClipboardRuntime:
    return ClipboardRuntime()


class ClipboardInlineSession(QmlPluginSession):
    """Inline clipboard session controlled by the launcher input box."""

    def __init__(self, *, manifest, view_model: ClipboardWindowViewModel) -> None:
        super().__init__(
            manifest=manifest,
            launch_mode=manifest.primary_command.launch_mode,
            view_model=view_model,
        )
        self._clipboard_view_model = view_model

    def on_input_changed(self, text: str) -> list[dict]:
        self._clipboard_view_model.refreshHistory(text)
        return []

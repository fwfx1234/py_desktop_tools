from __future__ import annotations

import sys

from app.services.clipboard import ClipboardService, DEFAULT_CLIPBOARD_CONFIG
from app.storage import StorageManager


def _create_backend():
    if sys.platform == "win32":
        from app.services.clipboard.backends.win32_backend import Win32ClipboardBackend

        return Win32ClipboardBackend()
    if sys.platform == "darwin":
        try:
            from app.services.clipboard.backends.macos_backend import MacOSClipboardBackend

            return MacOSClipboardBackend()
        except Exception:
            from app.services.clipboard.backends.pyperclip_backend import PyperclipClipboardBackend

            return PyperclipClipboardBackend()
    from app.services.clipboard.backends.noop_backend import NoopClipboardBackend

    return NoopClipboardBackend()


class ClipboardRuntime:
    def __init__(self) -> None:
        self._service: ClipboardService | None = None

    def on_background_start(self, ctx) -> None:
        if self._service is not None:
            return
        existing = ctx.services.clipboard
        if isinstance(existing, ClipboardService):
            self._service = existing
            return
        storage = ctx.services.storage
        if not isinstance(storage, StorageManager):
            raise RuntimeError("Storage manager is unavailable")
        self._service = ClipboardService(
            storage.database(
                "clipboard.db",
                row_factory=None,
                check_same_thread=False,
            ),
            settings_store=storage.dict_store(
                "clipboard/settings",
                defaults=DEFAULT_CLIPBOARD_CONFIG,
            ),
            backend=_create_backend(),
        )
        self._service.start()
        ctx.services.clipboard = self._service

    def on_enter(self, ctx, action):
        service = self._service or ctx.services.clipboard
        if service is None:
            self.on_background_start(ctx)
            service = self._service
        if not isinstance(service, ClipboardService):
            raise RuntimeError("Clipboard background service is unavailable")

        from .view_model import ClipboardWindowViewModel

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


class ClipboardInlineSession:
    def __init__(self, *, manifest, view_model) -> None:
        self.manifest = manifest
        self.launch_mode = manifest.primary_command.launch_mode
        self._clipboard_view_model = view_model

    def create_qml_context(self) -> dict:
        if not self.manifest.context_property:
            return {}
        return {self.manifest.context_property: self._clipboard_view_model}

    def qml_page(self) -> str:
        return self.manifest.qml_page

    def list_model(self) -> list[dict]:
        return []

    def on_input_changed(self, text: str) -> list[dict]:
        self._clipboard_view_model.refreshHistory(text)
        return []

    def on_list_item_selected(self, item_id: str) -> None:
        del item_id
        return

    def on_list_item_action(self, item_id: str, action_id: str) -> list[dict]:
        del item_id, action_id
        return []

    def reactivate(self, action) -> None:
        if action.input_text:
            self.on_input_changed(action.input_text)

    def close(self) -> None:
        if self._clipboard_view_model is not None:
            self._clipboard_view_model.deleteLater()
            self._clipboard_view_model = None

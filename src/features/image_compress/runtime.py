from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote, urlparse

from app.commands.context import IMAGE_EXTENSIONS
from app.plugins.runtime import PluginAction, PluginContext, QmlPluginSession

from .view_model import ImageCompressViewModel


class ImageCompressRuntime:
    def on_enter(self, ctx: PluginContext, action: PluginAction) -> QmlPluginSession:
        files = _image_files_from_input(action.input_text)
        if not files:
            files = _latest_clipboard_image_files(ctx)
        view_model = ImageCompressViewModel(files)
        return ImageCompressSession(action.manifest, view_model)

    def on_exit(self) -> None:
        return


class ImageCompressSession(QmlPluginSession):
    def __init__(self, manifest, view_model: ImageCompressViewModel) -> None:
        super().__init__(
            manifest=manifest,
            launch_mode=manifest.primary_command.launch_mode,
            view_model=view_model,
        )
        self._image_view_model = view_model

    def on_input_changed(self, text: str) -> list[dict]:
        files = _image_files_from_input(text)
        if files:
            self._image_view_model.setFiles(files)
        return []


def create_runtime() -> ImageCompressRuntime:
    return ImageCompressRuntime()


def _latest_clipboard_image_files(ctx: PluginContext) -> list[str]:
    service = ctx.services.get("clipboard.background")
    store = getattr(service, "store", None)
    latest_item = getattr(store, "latest_item", None)
    if not callable(latest_item):
        return []
    try:
        item = latest_item()
    except Exception:
        return []
    if not isinstance(item, dict):
        return []

    item_type = str(item.get("itemType") or "").lower()
    if item_type == "image":
        return _filter_image_paths([str(item.get("content") or "")])
    if item_type == "files":
        metadata = item.get("metadata") or {}
        paths = metadata.get("paths") if isinstance(metadata, dict) else []
        if not isinstance(paths, list):
            paths = _parse_paths(str(item.get("content") or ""))
        return _filter_image_paths([str(path) for path in paths])
    return []


def _image_files_from_input(text: str) -> list[str]:
    value = text.strip()
    if not value:
        return []
    if value.startswith("["):
        return _filter_image_paths(_parse_paths(value))
    return _filter_image_paths([_normalize_path(value)])


def _parse_paths(content: str) -> list[str]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return []


def _normalize_path(value: str) -> str:
    path_text = value.strip().strip("\"'")
    if path_text.startswith("file://"):
        parsed = urlparse(path_text)
        path_text = unquote(parsed.path)
        if len(path_text) >= 3 and path_text[0] == "/" and path_text[2] == ":":
            path_text = path_text[1:]
    return path_text


def _filter_image_paths(paths: list[str]) -> list[str]:
    out: list[str] = []
    for raw in paths:
        path_text = _normalize_path(str(raw))
        if not path_text:
            continue
        path = Path(path_text)
        if path.suffix.lower() in IMAGE_EXTENSIONS and path.exists():
            out.append(str(path))
    return out

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse


IMAGE_EXTENSIONS = {
    ".apng",
    ".avif",
    ".bmp",
    ".gif",
    ".heic",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}


@dataclass(frozen=True, slots=True)
class LauncherContext:
    """Typed context used by command ranking."""

    input_text: str = ""
    input_body: str = ""
    prefix: str = ""
    detected_input_kinds: frozenset[str] = field(default_factory=frozenset)
    clipboard_type: str = ""
    clipboard_preview: str = ""
    clipboard_text: str = ""
    detected_clipboard_kinds: frozenset[str] = field(default_factory=frozenset)


def build_launcher_context(
    input_text: str,
    known_prefixes: set[str] | list[str] | tuple[str, ...] | frozenset[str],
    latest_clipboard_item: dict | None = None,
) -> LauncherContext:
    """Create launcher context without importing plugin runtimes."""

    prefix, body = parse_input_prefix(input_text, known_prefixes)
    search_text = body if prefix else input_text
    clipboard_text, clipboard_type, clipboard_preview, clipboard_kinds = (
        detect_clipboard_kinds(latest_clipboard_item)
    )
    return LauncherContext(
        input_text=input_text,
        input_body=body if prefix else input_text,
        prefix=prefix,
        detected_input_kinds=detect_text_kinds(search_text),
        clipboard_type=clipboard_type,
        clipboard_preview=clipboard_preview,
        clipboard_text=clipboard_text,
        detected_clipboard_kinds=clipboard_kinds,
    )


def parse_input_prefix(
    input_text: str,
    known_prefixes: set[str] | list[str] | tuple[str, ...] | frozenset[str],
) -> tuple[str, str]:
    """Return (prefix, body) when input starts with a declared command prefix."""

    text = input_text.strip()
    if not text:
        return "", ""
    prefix_set = {str(item).strip().lower() for item in known_prefixes if str(item).strip()}
    if not prefix_set:
        return "", text

    parts = text.split(maxsplit=1)
    if not parts:
        return "", text
    candidate = parts[0].lower()
    if candidate not in prefix_set:
        return "", text
    return candidate, (parts[1] if len(parts) > 1 else "").strip()


def detect_text_kinds(text: str) -> frozenset[str]:
    """Detect generic input kinds understood by the command service."""

    value = text.strip()
    if not value:
        return frozenset()

    kinds: set[str] = {"text"}
    if _is_json_text(value):
        kinds.add("json")
    if _is_url(value):
        kinds.add("url")

    path = _path_from_text(value)
    if path is not None:
        kinds.add("file")
        if path.suffix.lower() in IMAGE_EXTENSIONS:
            kinds.add("image_file")

    return frozenset(kinds)


def detect_clipboard_kinds(item: dict | None) -> tuple[str, str, str, frozenset[str]]:
    """Return clipboard text, type, preview, and generic kinds."""

    if not item:
        return "", "", "", frozenset()

    item_type = str(item.get("itemType") or item.get("item_type") or "").strip().lower()
    content = str(item.get("content") or "")
    preview = str(item.get("preview") or "")
    kinds: set[str] = {"clipboard"}

    if item_type == "text":
        kinds.update(detect_text_kinds(content or preview))
    elif item_type == "image":
        kinds.add("image")
    elif item_type == "files":
        kinds.add("file")
        paths = _clipboard_file_paths(item)
        if any(Path(path).suffix.lower() in IMAGE_EXTENSIONS for path in paths):
            kinds.add("image_file")

    return content, item_type, preview, frozenset(kinds)


def _is_json_text(text: str) -> bool:
    if not (text.startswith("{") or text.startswith("[")):
        return False
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, (dict, list))


def _is_url(text: str) -> bool:
    candidate = text.strip()
    if candidate.startswith("www."):
        candidate = "https://" + candidate
    parsed = urlparse(candidate)
    return parsed.scheme in {"http", "https", "ws", "wss"} and bool(parsed.netloc)


def _path_from_text(text: str) -> Path | None:
    value = text.strip().strip("\"'")
    if value.startswith("file://"):
        parsed = urlparse(value)
        value = unquote(parsed.path)
        if re.match(r"^/[A-Za-z]:/", value):
            value = value[1:]
    if not value:
        return None

    try:
        path = Path(value)
    except (OSError, ValueError):
        return None

    if path.exists() or path.suffix.lower() in IMAGE_EXTENSIONS:
        return path
    return None


def _clipboard_file_paths(item: dict) -> list[str]:
    metadata = item.get("metadata") or {}
    if isinstance(metadata, dict):
        paths = metadata.get("paths") or []
        if isinstance(paths, list):
            return [str(path) for path in paths if path]

    content = str(item.get("content") or "")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return [content] if content else []
    if isinstance(parsed, list):
        return [str(path) for path in parsed if path]
    return []

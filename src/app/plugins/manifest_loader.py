from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.paths import resource_root
from app.plugins.manifest import (
    CommandContribution,
    ContextMatcher,
    LaunchMode,
    MatcherSource,
    PluginActivation,
    PluginManifest,
)


DEFAULT_PLUGIN_DIR_NAME = "plugins"
DEFAULT_BUNDLED_PLUGIN_DIR_NAME = "features"
DEFAULT_EXTERNAL_ORDER_START = 1000


def default_bundled_plugin_dirs() -> list[Path]:
    """Return plugin package roots shipped with this app."""

    root = resource_root()
    candidates = [
        root / "src" / DEFAULT_BUNDLED_PLUGIN_DIR_NAME,
        root / DEFAULT_BUNDLED_PLUGIN_DIR_NAME,
    ]
    return [path for path in candidates if path.is_dir()]


def default_external_plugin_dirs() -> list[Path]:
    """Return user/plugin search directories without creating them."""

    configured = os.getenv("PY_DESKTOP_TOOLS_PLUGIN_DIR", "").strip()
    if configured:
        return [
            Path(item).expanduser()
            for item in configured.split(os.pathsep)
            if item.strip()
        ]
    return [Path(__file__).parents[3] / DEFAULT_PLUGIN_DIR_NAME]


def default_plugin_dirs() -> list[Path]:
    """Return all default plugin roots, bundled first then user plugins."""

    return default_bundled_plugin_dirs() + default_external_plugin_dirs()


def load_all_plugin_manifests() -> list[PluginManifest]:
    """Load bundled and user plugin packages through the same parser."""

    return merge_manifests(
        load_bundled_manifests(),
        load_external_manifests(),
    )


def load_bundled_manifests(
    plugin_dirs: list[Path] | None = None,
    *,
    start_order: int = 0,
) -> list[PluginManifest]:
    """Load app-shipped plugin packages from the bundled plugin roots."""

    return load_plugin_manifests(
        plugin_dirs or default_bundled_plugin_dirs(),
        start_order=start_order,
    )


def load_external_manifests(
    plugin_dirs: list[Path] | None = None,
    *,
    start_order: int = DEFAULT_EXTERNAL_ORDER_START,
) -> list[PluginManifest]:
    """Load user/plugin packages from configured plugin roots."""

    return load_plugin_manifests(
        plugin_dirs or default_external_plugin_dirs(),
        start_order=start_order,
    )


def load_plugin_manifests(
    plugin_dirs: list[Path],
    *,
    start_order: int = 0,
) -> list[PluginManifest]:
    """Load plugin manifest files from plugin package directories.

    A plugin root may contain plugin packages as direct child directories. A
    package can provide either plugin.json or one or more *.plugin.json files.
    Multiple manifest files in one package share the same package_dir and are
    useful for small bundled system plugins that share runtime code.
    """

    manifests: list[PluginManifest] = []
    seen: set[str] = set()
    for root in plugin_dirs:
        if not root.is_dir():
            continue
        for manifest_path in discover_manifest_files(root):
            try:
                manifest = load_manifest_file(manifest_path)
            except Exception as exc:
                print(f"[WARN] 插件 Manifest 加载失败: {manifest_path} - {exc}")
                continue
            if manifest.id in seen:
                print(f"[WARN] 插件 id 重复，已忽略: {manifest.id} ({manifest_path})")
                continue
            seen.add(manifest.id)
            if manifest.order == 99:
                manifest = manifest.with_order(start_order + len(manifests))
            manifests.append(manifest)
    return sorted(manifests, key=lambda item: item.order)


def discover_manifest_files(plugin_root: Path) -> list[Path]:
    """Find plugin.json and *.plugin.json files below one plugin root."""

    candidates: set[Path] = set()
    if plugin_root.is_file() and plugin_root.name.endswith(".json"):
        candidates.add(plugin_root)
    elif plugin_root.is_dir():
        for pattern in ("plugin.json", "*.plugin.json"):
            candidates.update(path for path in plugin_root.glob(pattern) if path.is_file())
        for child in plugin_root.iterdir():
            if not child.is_dir():
                continue
            for pattern in ("plugin.json", "*.plugin.json"):
                candidates.update(path for path in child.glob(pattern) if path.is_file())
    return sorted(candidates)


def load_manifest_file(manifest_path: Path) -> PluginManifest:
    """Parse one plugin.json file into a PluginManifest."""

    package_dir = manifest_path.parent.resolve()
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("manifest root must be an object")

    plugin_id = _required_str(raw, "id")
    name = _required_str(raw, "name")
    entrypoint = _required_str(raw, "entrypoint")
    commands = [
        _parse_command(item, plugin_id, package_dir)
        for item in _list(raw.get("commands"))
    ]

    return PluginManifest(
        id=plugin_id,
        name=name,
        version=str(raw.get("version") or "0.1.0"),
        description=str(raw.get("description") or ""),
        icon=_resolve_icon(str(raw.get("icon") or ""), package_dir),
        entrypoint=entrypoint,
        qml_page=_resolve_plugin_path(str(raw.get("qmlPage") or ""), package_dir),
        context_property=str(raw.get("contextProperty") or ""),
        category=str(raw.get("category") or "tool"),
        order=_int(raw.get("order"), 99),
        activation=_activation(raw.get("activation")),
        window_options=raw.get("window") if isinstance(raw.get("window"), dict) else {},
        commands=commands,
        package_dir=package_dir,
    )


def merge_manifests(
    primary: list[PluginManifest],
    secondary: list[PluginManifest],
) -> list[PluginManifest]:
    """Merge manifest groups; earlier groups win on duplicate ids."""

    by_id = {manifest.id: manifest for manifest in primary}
    for manifest in secondary:
        if manifest.id in by_id:
            print(f"[WARN] 插件 id 重复，已忽略后加载项: {manifest.id}")
            continue
        by_id[manifest.id] = manifest
    return sorted(by_id.values(), key=lambda item: item.order)


def _parse_command(
    raw: object,
    plugin_id: str,
    package_dir: Path,
) -> CommandContribution:
    if not isinstance(raw, dict):
        raise ValueError("command must be an object")
    command_id = str(raw.get("id") or f"{plugin_id}.open")
    return CommandContribution(
        id=command_id,
        title=str(raw.get("title") or raw.get("name") or command_id),
        subtitle=str(raw.get("subtitle") or raw.get("description") or ""),
        icon=_resolve_icon(str(raw.get("icon") or ""), package_dir),
        keywords=[str(item) for item in _list(raw.get("keywords"))],
        prefixes=[str(item) for item in _list(raw.get("prefixes"))],
        matchers=[_parse_matcher(item) for item in _list(raw.get("matchers"))],
        launch_mode=_launch_mode(raw.get("launchMode") or raw.get("launch_mode")),
        input_mode=_input_mode(raw.get("inputMode") or raw.get("input_mode")),
        hotkey=str(raw.get("hotkey") or "").strip(),
        payload=raw.get("payload") if isinstance(raw.get("payload"), dict) else {},
    )


def _parse_matcher(raw: object) -> ContextMatcher:
    if not isinstance(raw, dict):
        raise ValueError("matcher must be an object")
    return ContextMatcher(
        source=_matcher_source(raw.get("source")),
        kind=str(raw.get("kind") or ""),
        boost=_int(raw.get("boost"), 0),
        pattern=str(raw.get("pattern") or ""),
    )


def _resolve_plugin_path(value: str, package_dir: Path) -> str:
    if not value:
        return ""
    if "://" in value or Path(value).is_absolute():
        return value
    return (package_dir / value).resolve().as_uri()


def _resolve_icon(value: str, package_dir: Path) -> str:
    if not value or value.startswith("qta:") or "://" in value:
        return value
    path = Path(value)
    if path.is_absolute():
        return path.resolve().as_uri()
    if "/" in value or "\\" in value or path.suffix:
        return (package_dir / value).resolve().as_uri()
    return value


def _required_str(raw: dict[str, Any], key: str) -> str:
    value = str(raw.get(key) or "").strip()
    if not value:
        raise ValueError(f"missing required field: {key}")
    return value


def _list(value: object) -> list:
    return value if isinstance(value, list) else []


def _int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _activation(value: object) -> PluginActivation:
    text = str(value or "lazy")
    return text if text in {"lazy", "background"} else "lazy"  # type: ignore[return-value]


def _launch_mode(value: object) -> LaunchMode:
    text = str(value or "inline_view")
    return text if text in {"none", "list", "inline_view", "window"} else "inline_view"  # type: ignore[return-value]


def _input_mode(value: object) -> str:
    text = str(value or "plugin")
    return text if text in {"global", "plugin"} else "plugin"


def _matcher_source(value: object) -> MatcherSource:
    text = str(value or "input")
    return text if text in {"input", "clipboard"} else "input"  # type: ignore[return-value]

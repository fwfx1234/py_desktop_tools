from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse

from app.paths import project_root
from app.plugins.manifest import PluginManifest
from app.plugins.manifest_loader import discover_manifest_files, load_all_plugin_manifests, load_manifest_file


DEFAULT_IMPORTED_PLUGIN_DIR = project_root() / "plugins"
PLUGIN_ARCHIVE_EXTENSIONS = {".zip"}


@dataclass(frozen=True, slots=True)
class PluginImportResult:
    ok: bool
    message: str
    code: str = ""
    plugin_ids: list[str] = field(default_factory=list)
    target_dir: str = ""

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "message": self.message,
            "code": self.code,
            "pluginIds": list(self.plugin_ids),
            "targetDir": self.target_dir,
        }


def import_plugin_package(source: str | Path) -> PluginImportResult:
    source_path = _normalize_source(source)
    if not source_path.exists():
        return PluginImportResult(False, "插件路径不存在", "not_found")
    try:
        if source_path.is_dir():
            return _import_from_dir(source_path)
        if source_path.is_file() and source_path.suffix.lower() in PLUGIN_ARCHIVE_EXTENSIONS:
            return _import_from_zip(source_path)
        return PluginImportResult(False, "请选择插件目录或 .zip 插件包", "unsupported_source")
    except Exception as exc:
        return PluginImportResult(False, f"导入失败: {exc}", "import_failed")


def imported_plugin_root() -> Path:
    root = _first_external_plugin_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _import_from_dir(source_dir: Path) -> PluginImportResult:
    manifests, package_dirs = _validate_package_tree(source_dir)
    _validate_plugin_ids_available(manifests)
    target_dir = _copy_packages(package_dirs)
    plugin_ids = [manifest.id for manifest in manifests]
    return PluginImportResult(
        True,
        f"已导入插件: {', '.join(plugin_ids)}",
        plugin_ids=plugin_ids,
        target_dir=str(target_dir),
    )


def _import_from_zip(source_file: Path) -> PluginImportResult:
    with tempfile.TemporaryDirectory(prefix="suishou_plugin_import_") as tmp:
        extract_root = Path(tmp)
        _extract_zip(source_file, extract_root)
        manifests, package_dirs = _validate_package_tree(extract_root)
        _validate_plugin_ids_available(manifests)
        target_dir = _copy_packages(package_dirs, fallback_name=source_file.stem)
        plugin_ids = [manifest.id for manifest in manifests]
        return PluginImportResult(
            True,
            f"已导入插件: {', '.join(plugin_ids)}",
            plugin_ids=plugin_ids,
            target_dir=str(target_dir),
        )


def _validate_package_tree(root: Path) -> tuple[list[PluginManifest], list[Path]]:
    manifest_paths = discover_manifest_files(root)
    if not manifest_paths:
        raise ValueError("未找到 plugin.json 或 *.plugin.json")
    root_resolved = root.resolve()
    if any(path.parent.resolve() == root_resolved for path in manifest_paths):
        manifest_paths = [path for path in manifest_paths if path.parent.resolve() == root_resolved]

    manifests: list[PluginManifest] = []
    seen_ids: set[str] = set()
    package_dirs: set[Path] = set()
    for manifest_path in manifest_paths:
        manifest = load_manifest_file(manifest_path)
        if manifest.id in seen_ids:
            raise ValueError(f"插件 id 重复: {manifest.id}")
        seen_ids.add(manifest.id)
        package_dirs.add(manifest_path.parent.resolve())
        _validate_manifest_assets(manifest, manifest_path)
        manifests.append(manifest)
    if not manifests:
        raise ValueError("未找到有效插件清单")
    return manifests, sorted(package_dirs)


def _validate_manifest_assets(manifest: PluginManifest, manifest_path: Path) -> None:
    module_name, separator, factory_name = manifest.entrypoint.partition(":")
    if not separator or not module_name.strip() or not factory_name.strip():
        raise ValueError(f"{manifest_path.name} 的 entrypoint 非法")

    package_dir = manifest_path.parent.resolve()
    local_module = package_dir.joinpath(*module_name.strip().split(".")).with_suffix(".py")
    if not local_module.is_file():
        raise ValueError(f"找不到 runtime 模块: {module_name.strip()}")

    if manifest.qml_page:
        qml_path = _local_file_from_uri(manifest.qml_page)
        if qml_path is not None and not qml_path.is_file():
            raise ValueError(f"找不到 QML 页面: {qml_path.name}")


def _copy_packages(package_dirs: list[Path], *, fallback_name: str = "") -> Path:
    root = imported_plugin_root()
    targets = [
        _copy_package(
            package_dir,
            root,
            fallback_name=fallback_name if len(package_dirs) == 1 else "",
        )
        for package_dir in package_dirs
    ]
    return targets[0] if len(targets) == 1 else root


def _copy_package(package_dir: Path, root: Path, *, fallback_name: str = "") -> Path:
    target_name = _safe_dir_name(fallback_name or package_dir.name or "plugin")
    target_dir = _unique_target_dir(root / target_name)
    target_dir.mkdir(parents=True, exist_ok=False)
    for item in package_dir.iterdir():
        destination = target_dir / item.name
        if item.is_dir():
            shutil.copytree(
                item,
                destination,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
            )
        else:
            shutil.copy2(item, destination)
    return target_dir


def _validate_plugin_ids_available(manifests: list[PluginManifest]) -> None:
    existing_ids = {manifest.id for manifest in load_all_plugin_manifests()}
    duplicates = sorted(manifest.id for manifest in manifests if manifest.id in existing_ids)
    if duplicates:
        raise ValueError(f"插件 id 已存在: {', '.join(duplicates)}")


def _extract_zip(source_file: Path, target_dir: Path) -> None:
    with zipfile.ZipFile(source_file) as archive:
        for member in archive.infolist():
            member_path = target_dir / member.filename
            if not _is_relative_to(member_path.resolve(), target_dir.resolve()):
                raise ValueError("压缩包包含越界路径")
        archive.extractall(target_dir)


def _first_external_plugin_dir() -> Path:
    configured = os.getenv("PY_DESKTOP_TOOLS_PLUGIN_DIR", "").strip()
    if configured:
        for item in configured.split(os.pathsep):
            text = item.strip()
            if text:
                return Path(text).expanduser()
    return DEFAULT_IMPORTED_PLUGIN_DIR


def _normalize_source(source: str | Path) -> Path:
    text = str(source).strip().strip("\"'")
    if text.startswith("file://"):
        parsed = urlparse(text)
        text = unquote(parsed.path)
        if len(text) >= 3 and text[0] == "/" and text[2] == ":":
            text = text[1:]
    return Path(text).expanduser().resolve()


def _local_file_from_uri(value: str) -> Path | None:
    if not value.startswith("file://"):
        return None
    parsed = urlparse(value)
    text = unquote(parsed.path)
    if len(text) >= 3 and text[0] == "/" and text[2] == ":":
        text = text[1:]
    return Path(text)


def _safe_dir_name(value: str) -> str:
    text = value.strip().replace(" ", "-")
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in text)
    return safe.strip(".-") or "plugin"


def _unique_target_dir(target_dir: Path) -> Path:
    if not target_dir.exists():
        return target_dir
    index = 2
    while True:
        candidate = target_dir.with_name(f"{target_dir.name}-{index}")
        if not candidate.exists():
            return candidate
        index += 1


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False

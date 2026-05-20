from __future__ import annotations

import ast
import hashlib
import plistlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.platform.models import AppEntry

_APP_DIRS = [
    Path("/Applications"),
    Path.home() / "Applications",
    Path("/System/Applications"),
    Path("/Applications/Utilities"),
]
_CHINESE_LOCALES = ("zh_cn", "zh_hans", "zh", "zh_tw", "zh_hant")
_ENGLISH_LOCALES = ("en", "en_us", "en_gb")
_STRINGS_PAIR_RE = re.compile(
    r'(?:"((?:\\.|[^"\\])*)"|([A-Za-z0-9_.$-]+))\s*=\s*"((?:\\.|[^"\\])*)"\s*;'
)


class MacOSAppIndexer:
    def __init__(self, app_dirs: list[Path] | None = None) -> None:
        self._app_dirs = _APP_DIRS if app_dirs is None else app_dirs

    def scan_apps(
        self,
        icon_dir: Path | None = None,
        *,
        extract_icons: bool = True,
    ) -> list[AppEntry]:
        if icon_dir is not None and extract_icons:
            icon_dir.mkdir(parents=True, exist_ok=True)
        seen: set[str] = set()
        apps: list[AppEntry] = []
        for root in self._app_dirs:
            if not root.is_dir():
                continue
            for app_dir in _iter_app_bundles(root):
                launch_path = str(app_dir.resolve())
                if launch_path in seen:
                    continue
                seen.add(launch_path)
                info = _read_info_plist(app_dir)
                name, aliases = _app_display_names(app_dir, info)
                bundle_id = str(info.get("CFBundleIdentifier") or "")
                icon_path = ""
                if icon_dir is not None and extract_icons:
                    icon_source = _find_icon_source(app_dir, info)
                    if icon_source is not None:
                        icon_key = hashlib.md5(launch_path.encode()).hexdigest()[:12]
                        icon_path = _convert_icon(icon_source, icon_dir / f"{icon_key}-v2.png")
                apps.append(
                    AppEntry(
                        platform="macos",
                        name=name,
                        launch_path=launch_path,
                        bundle_id=bundle_id,
                        icon_path=icon_path,
                        aliases=aliases,
                    )
                )
        return apps

    def quick_signature(self) -> str:
        digest = hashlib.sha256()
        count = 0
        for root in self._app_dirs:
            if not root.is_dir():
                continue
            for app_dir in _iter_app_bundles(root):
                try:
                    resolved = app_dir.resolve()
                    stat = resolved.stat()
                except OSError:
                    continue
                count += 1
                digest.update(str(resolved).encode("utf-8", errors="ignore"))
                digest.update(b"\0")
                digest.update(str(stat.st_mtime_ns).encode("ascii"))
                digest.update(b"\0")
        return f"macos-apps-v2:{count}:{digest.hexdigest()}"


def _iter_app_bundles(root: Path) -> list[Path]:
    apps: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            children = sorted(current.iterdir(), key=lambda item: item.name.lower())
        except OSError:
            continue
        for child in children:
            if not child.is_dir():
                continue
            if child.suffix.lower() == ".app":
                apps.append(child)
                continue
            stack.append(child)
    return apps


def _read_info_plist(app_dir: Path) -> dict:
    info_path = app_dir / "Contents" / "Info.plist"
    if not info_path.is_file():
        return {}
    try:
        with info_path.open("rb") as file_obj:
            raw = plistlib.load(file_obj)
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _app_display_names(app_dir: Path, info: dict) -> tuple[str, list[str]]:
    base_names = _bundle_name_candidates(info, app_dir.stem)
    localized_names = _localized_bundle_names(app_dir)
    chinese_names = _names_for_locales(localized_names, _CHINESE_LOCALES)
    english_names = _names_for_locales(localized_names, _ENGLISH_LOCALES)
    all_localized = [
        name
        for locale, names in localized_names.items()
        if locale not in set(_CHINESE_LOCALES) | set(_ENGLISH_LOCALES)
        for name in names
    ]
    display_name = _unique_strings(chinese_names + base_names)[0]
    aliases = _unique_strings(english_names + base_names + chinese_names + all_localized)
    aliases = [alias for alias in aliases if alias != display_name]
    return display_name, aliases


def _localized_bundle_names(app_dir: Path) -> dict[str, list[str]]:
    resources = app_dir / "Contents" / "Resources"
    if not resources.is_dir():
        return {}
    names: dict[str, list[str]] = {}
    try:
        lproj_dirs = sorted(resources.glob("*.lproj"), key=lambda item: item.name.lower())
    except OSError:
        return {}
    for lproj_dir in lproj_dirs:
        if not lproj_dir.is_dir():
            continue
        strings = _read_info_plist_strings(lproj_dir / "InfoPlist.strings")
        candidates = _bundle_name_candidates(strings, "")
        if candidates:
            names[_locale_key(lproj_dir.name)] = candidates
    return names


def _read_info_plist_strings(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        raw = path.read_bytes()
    except OSError:
        return {}
    try:
        parsed = plistlib.loads(raw)
        if isinstance(parsed, dict):
            return {str(key): str(value) for key, value in parsed.items()}
    except Exception:
        pass
    for encoding in (
        "utf-16",
        "utf-16-le",
        "utf-16-be",
        "utf-8-sig",
        "utf-8",
        "gb18030",
    ):
        try:
            text = raw.decode(encoding)
        except UnicodeError:
            continue
        parsed = _parse_info_plist_strings(text)
        if parsed:
            return parsed
    return {}


def _parse_info_plist_strings(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for match in _STRINGS_PAIR_RE.finditer(text):
        key = _decode_strings_token(match.group(1) or match.group(2) or "").strip()
        value = _decode_strings_token(match.group(3)).strip()
        if key and value:
            out[key] = value
    return out


def _decode_strings_token(value: str) -> str:
    fixed = re.sub(r"\\U([0-9A-Fa-f]{4})(?![0-9A-Fa-f])", r"\\u\1", value)
    try:
        decoded = ast.literal_eval(f'"{fixed}"')
    except Exception:
        return value.replace('\\"', '"').replace("\\\\", "\\")
    return str(decoded)


def _bundle_name_candidates(info: dict, fallback: str) -> list[str]:
    return _unique_strings(
        [
            str(info.get("CFBundleDisplayName") or ""),
            str(info.get("CFBundleName") or ""),
            fallback,
        ]
    )


def _names_for_locales(
    names_by_locale: dict[str, list[str]],
    locales: tuple[str, ...],
) -> list[str]:
    names: list[str] = []
    for locale in locales:
        names.extend(names_by_locale.get(locale, []))
    return names


def _locale_key(name: str) -> str:
    raw = name[:-6] if name.lower().endswith(".lproj") else name
    return raw.replace("-", "_").lower()


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = value.strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            out.append(text)
    return out


def _find_icon_source(app_dir: Path, info: dict) -> Path | None:
    resources = app_dir / "Contents" / "Resources"
    candidates: list[str] = []
    raw_icon = info.get("CFBundleIconFile")
    if isinstance(raw_icon, str):
        candidates.append(raw_icon)
    raw_icon_name = info.get("CFBundleIconName")
    if isinstance(raw_icon_name, str):
        candidates.append(raw_icon_name)
    raw_icons = info.get("CFBundleIcons")
    if isinstance(raw_icons, dict):
        primary_icon = raw_icons.get("CFBundlePrimaryIcon")
        if isinstance(primary_icon, dict):
            icon_files = primary_icon.get("CFBundleIconFiles")
            if isinstance(icon_files, list):
                candidates.extend(str(item) for item in icon_files if item)

    for candidate in candidates:
        icon_path = _resolve_resource_icon(resources, candidate)
        if icon_path is not None:
            return icon_path

    try:
        return next(resources.glob("*.icns"))
    except StopIteration:
        return None


def _resolve_resource_icon(resources: Path, value: str) -> Path | None:
    raw = value.strip()
    if not raw:
        return None
    path = Path(raw)
    if path.is_absolute() and path.is_file():
        return path
    names = [raw]
    if not Path(raw).suffix:
        names.extend([f"{raw}.icns", f"{raw}.png"])
    for name in names:
        candidate = resources / name
        if candidate.is_file():
            return candidate
    return None


def _convert_icon(icon_path: Path, out_path: Path) -> str:
    if out_path.exists() and out_path.stat().st_size > 0:
        return str(out_path)
    if icon_path.suffix.lower() == ".icns":
        converted = _convert_icns_with_iconutil(icon_path, out_path)
        if converted:
            return converted
    return _convert_icon_with_pillow(icon_path, out_path)


def _convert_icns_with_iconutil(icon_path: Path, out_path: Path) -> str:
    if shutil.which("iconutil") is None:
        return ""
    try:
        with tempfile.TemporaryDirectory(prefix="py_desktop_tools_icon_") as tmp:
            iconset_dir = Path(tmp) / "icon.iconset"
            subprocess.run(
                ["iconutil", "-c", "iconset", str(icon_path), "-o", str(iconset_dir)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            pngs = list(iconset_dir.glob("*.png"))
            if not pngs:
                return ""
            return _save_best_png(pngs, out_path)
    except Exception:
        return ""


def _save_best_png(paths: list[Path], out_path: Path) -> str:
    try:
        from PIL import Image

        candidates = []
        for path in paths:
            try:
                with Image.open(path) as image:
                    width, height = image.size
                    alpha = image.convert("RGBA").getchannel("A").getextrema()
                    candidates.append((path, width, height, alpha))
            except Exception:
                continue
        if not candidates:
            return ""
        path, _, _, _ = min(
            candidates,
            key=lambda item: (
                item[3][0] == 255 and item[3][1] == 255,
                abs(max(item[1], item[2]) - 128),
                -item[1] * item[2],
            ),
        )
        with Image.open(path) as image:
            selected = image.convert("RGBA")
            selected.thumbnail((128, 128), Image.Resampling.LANCZOS)
            selected.save(out_path, "PNG")
        if out_path.exists() and out_path.stat().st_size > 0:
            return str(out_path)
    except Exception:
        return ""
    return ""


def _convert_icon_with_pillow(icon_path: Path, out_path: Path) -> str:
    try:
        from PIL import Image, ImageSequence

        with Image.open(icon_path) as image:
            frames = []
            for frame in ImageSequence.Iterator(image):
                frame.load()
                frames.append(frame.convert("RGBA"))
            if not frames:
                frames = [image.convert("RGBA")]
            selected = max(frames, key=lambda item: item.width * item.height)
            selected.thumbnail((64, 64), Image.Resampling.LANCZOS)
            selected.save(out_path, "PNG")
        if out_path.exists() and out_path.stat().st_size > 0:
            return str(out_path)
    except Exception:
        return ""
    return ""

from __future__ import annotations

import os
import sys
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return project_root()


def user_data_dir() -> Path:
    configured = os.getenv("PY_DESKTOP_TOOLS_DATA_DIR", "").strip()
    if configured:
        root = Path(configured)
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support" / "PyDesktopTools"
    elif os.name == "nt":
        root = Path(os.getenv("APPDATA", str(Path.home()))) / "PyDesktopTools"
    else:
        root = Path.home() / ".local" / "share" / "py-desktop-tools"
    root.mkdir(parents=True, exist_ok=True)
    return root


def data_dir() -> Path:
    return user_data_dir()


def db_path(name: str) -> Path:
    return data_dir() / name


def cache_dir() -> Path:
    root = data_dir() / "cache"
    root.mkdir(parents=True, exist_ok=True)
    return root


def plugin_dirs() -> list[Path]:
    values = os.getenv("PY_DESKTOP_TOOLS_PLUGIN_DIR", "").strip()
    if not values:
        return [project_root() / "plugins"]
    return [Path(item.strip()) for item in values.split(os.pathsep) if item.strip()]

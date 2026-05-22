# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Suishou (PySide6 + QML)."""

import os
import sys
from pathlib import Path

# ── paths ────────────────────────────────────────────────────────────────────
# The build script always runs PyInstaller from the project root.
PROJECT_ROOT = Path.cwd().resolve()
SRC = PROJECT_ROOT / "src"
APP_ICON_DIR = PROJECT_ROOT / "assets" / "app_icon"
MACOS_ICON = APP_ICON_DIR / "app_icon.icns"
WINDOWS_ICON = APP_ICON_DIR / "app_icon.ico"

if sys.platform == "darwin" and not MACOS_ICON.exists():
    raise FileNotFoundError(f"macOS app icon not found: {MACOS_ICON}")
if sys.platform == "win32" and not WINDOWS_ICON.exists():
    raise FileNotFoundError(f"Windows app icon not found: {WINDOWS_ICON}")

# ── collect QML / plugin.json / asset trees ──────────────────────────────────
def _walk_rel(dirpath: Path, *patterns: str) -> list[tuple[str, str]]:
    """Return (source, dest) pairs for glob patterns under dirpath, relative to cwd."""
    pairs = []
    for pat in patterns:
        for fp in sorted(dirpath.rglob(pat)):
            rel = fp.relative_to(PROJECT_ROOT)
            pairs.append((str(fp), str(rel.parent)))
    return pairs

# All QML files + JS helper. `qmldir` registers QML singletons (e.g. Theme) and
# `*.qmltypes` exposes typed C++ types; both must ship with the .qml sources or
# the engine silently fails to resolve `import "theme"` style relative imports.
qml_data = _walk_rel(SRC, "*.qml", "*.js", "qmldir", "*.qmltypes")

# Plugin manifests
manifest_data = _walk_rel(SRC, "plugin.json", "*.plugin.json")

plugin_python_data = _walk_rel(SRC / "features", "*.py")

# SVG icons
icon_data = _walk_rel(SRC, "*.svg")

# Web assets (xterm terminal)
web_assets = _walk_rel(SRC, "*.html", "*.css")
qta_icon_data = _walk_rel(PROJECT_ROOT / "assets" / "qta_icons", "*.png", "*.json")

# ── hidden imports ───────────────────────────────────────────────────────────
# PySide6 / Qt
HIDDEN_IMPORTS = [
    "PySide6.QtQuick",
    "PySide6.QtQuickControls2",
    "PySide6.QtQml",
    "PySide6.QtNetwork",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    # Feature modules
    "app",
    "app.commands",
    "app.concurrency",
    "app.launcher",
    "app.logging",
    "app.platform",
    "app.platform.common",
    "app.platform.macos",
    "app.platform.noop",
    "app.diagnostics",
    "app.diagnostics.memory",
    "app.plugins",
    "app.webengine",
    "app.services.clipboard",
    "app.services.clipboard.backends",
    "app.storage",
    "app.tray",
    "features",
]

# Platform-specific
if sys.platform == "darwin":
    HIDDEN_IMPORTS += [
        "pynput",
    ]
elif sys.platform == "win32":
    HIDDEN_IMPORTS += [
        "pylnk3",
    ]

EXCLUDE_IMPORTS = [
    "tkinter",
    "matplotlib",
    "notebook",
    "jupyter",
]

# ── datas ────────────────────────────────────────────────────────────────────
DATAS = qml_data + manifest_data + plugin_python_data + icon_data + web_assets + qta_icon_data

# ── block cipher (optional) ──────────────────────────────────────────────────
BLOCK_CIPHER_KEY = None

a = Analysis(
    [str(PROJECT_ROOT / "tools" / "pyinstaller_bootstrap.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDE_IMPORTS,
    noarchive=False,
    cipher=BLOCK_CIPHER_KEY,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="Suishou",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(WINDOWS_ICON) if sys.platform == "win32" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Suishou",
)

# ── macOS: wrap in .app bundle ───────────────────────────────────────────────
if sys.platform == "darwin":
    BUNDLE(
        coll,
        name="Suishou.app",
        icon=str(MACOS_ICON),
        bundle_identifier="com.suishou.app",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
        },
    )

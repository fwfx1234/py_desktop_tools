# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for PyDesktopTools (PySide6 + QML)."""

import os
import sys
from pathlib import Path

# ── paths ────────────────────────────────────────────────────────────────────
# The build script always runs PyInstaller from the project root.
PROJECT_ROOT = Path.cwd().resolve()
SRC = PROJECT_ROOT / "src"

# ── collect QML / plugin.json / asset trees ──────────────────────────────────
def _walk_rel(dirpath: Path, *patterns: str) -> list[tuple[str, str]]:
    """Return (source, dest) pairs for glob patterns under dirpath, relative to cwd."""
    pairs = []
    for pat in patterns:
        for fp in sorted(dirpath.rglob(pat)):
            rel = fp.relative_to(PROJECT_ROOT)
            pairs.append((str(fp), str(rel.parent)))
    return pairs

# All QML files + JS helper
qml_data = _walk_rel(SRC, "*.qml", "*.js")

# Plugin manifests
manifest_data = _walk_rel(SRC, "plugin.json", "*.plugin.json")

# SVG icons
icon_data = _walk_rel(SRC, "*.svg")

# Web assets (xterm terminal)
web_assets = _walk_rel(SRC, "*.html", "*.css")

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
    "app.plugins",
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
DATAS = qml_data + manifest_data + icon_data + web_assets

# ── block cipher (optional) ──────────────────────────────────────────────────
BLOCK_CIPHER_KEY = None

a = Analysis(
    [str(SRC / "app" / "main.py")],
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
    name="PyDesktopTools",
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
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PyDesktopTools",
)

# ── macOS: wrap in .app bundle ───────────────────────────────────────────────
if sys.platform == "darwin":
    BUNDLE(
        coll,
        name="PyDesktopTools.app",
        icon=None,
        bundle_identifier="com.py-desktop-tools.app",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
        },
    )

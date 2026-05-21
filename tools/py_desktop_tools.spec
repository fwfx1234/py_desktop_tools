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
# Use a fixed key so reproducible builds are possible.
# To generate a fresh key: pyinstaller --key $(python3 -c "import secrets; print(secrets.token_hex(16))")
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

# ── collect Qt QML deployment folder ─────────────────────────────────────────
# PyInstaller hooks for PySide6-QML usually cover this, but we be explicit.
# The ``--collect-all`` or ``--add-data`` approach via spec is fragile across
# PySide6 versions.  Instead we rely on the ``pyside6`` hook that ships with
# PyInstaller >= 6.x, which pulls in ``PySide6/qml/`` automatically.
# If you see missing QML modules at runtime, verify with:
#   find . -path '*/PySide6/qml/QtQuick*'  (inside the one-folder dist)

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
    icon=str(PROJECT_ROOT / "src" / "app" / "assets" / "icons" / "rocket.svg")
    if sys.platform == "darwin"
    and (PROJECT_ROOT / "src" / "app" / "assets" / "icons" / "rocket.svg").exists()
    else None,
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

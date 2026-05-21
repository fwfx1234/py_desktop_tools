#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --group build
uv run pyinstaller tools/py_desktop_tools.spec --noconfirm

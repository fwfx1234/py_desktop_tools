$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
uv sync --group build
uv run pyinstaller build\pyinstaller\py_desktop_tools.spec --noconfirm

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
uv sync --group build
uv run pyinstaller tools\py_desktop_tools.spec --noconfirm

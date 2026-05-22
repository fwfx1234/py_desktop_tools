$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
uv sync --group build
uv run python -m PyInstaller tools\suishou.spec --noconfirm

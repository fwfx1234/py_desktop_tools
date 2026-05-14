# AGENTS.md
# 始终使用中文交互
#系统是windows终端环境使用powershell

PySide6 + QML desktop toolbox with a uTools-like launcher (Alt+Space).

## Commands

```bash
uv run app          # run the app
uv sync             # sync dependencies
uv add <pkg>        # add a dependency
```

No lint/typecheck/test commands configured. Hot-reload QML: set `PY_DESKTOP_QML_HOT_RELOAD=1`.

## Architecture

```
src/
  app/           # kernel: main, launcher, commands, plugins, hotkey, tray, theme
  features/      # plugin modules (api_test, json_parser, qr, clipboard, etc.)
```

Each feature is a plugin with a `plugin.json` manifest. The kernel discovers them via `src/app/plugins/manifest_loader.py` which scans subdirectories of `src/features/` for `plugin.json` files.

**Entry point**: `src/app/main.py:main()`

**MVVM layering per feature**:
- `plugin.json` — declares commands, launch mode, entrypoint, QML page, context property
- `runtime.py` — factory for `SimpleQmlRuntime` that creates the ViewModel
- `view_model.py` — `QObject` subclass exposing `Signal`/`Slot`/`Property` for QML binding
- `service.py` — pure Python, no QML dependency
- `*.qml` — View, imports `app/ui`, `app/theme`, and feature-local `components/`

**QML global context properties** (injected in `main.py`):
- `app` → `AppViewModel`
- `launcherBridge` → `LauncherBridge`
- Plugin ViewModels (e.g. `apiTestVm`) are injected only while a plugin session is active

## Plugin system

- **Manifest**: `plugin.json` in feature directory. `entrypoint: "runtime:create_runtime"` → module `runtime.py`, function `create_runtime`. `qmlPage` resolves relative to `package_dir`.
- **Runtime loading**: `PluginManager._load_runtime()` — lazy, entrypoint parsed as `module:factory`, module imported via `importlib`. Creates synthetic packages so feature-local relative imports work.
- **Session lifecycle**: `PluginSessionManager.open_plugin()` → creates session, injects ViewModel into QML context via `contextProperty`, returns session. On close, sets context property to `None`.
- **Launch modes**: `window` (standalone window), `list` (inline list in launcher), `inline_view` (inline QML in launcher), `none` (execute and hide).
- **Background plugins** (`"activation": "background"`): runtime is never closed by `close_runtime()`.
- **Plugin IDs use hyphens** (e.g. `api-test`), not underscores.

## Key conventions

- **No comments** should be added to code unless explicitly requested.
- Python 3.13, package manager is `uv`, virtual env in `.venv`.
- `pyproject.toml` sets `where = ["src"]` for setuptools package discovery.
- Startup data: `data/` directory contains SQLite databases (e.g. `api_test.db`). Override with `PY_DESKTOP_TOOLS_DATA_DIR`.
- QML files import shared components via `import "../../app/ui"`, `import "../../app/theme"`.
- `_plugin_window_config()`: `width`/`height` < 1.0 = ratio of screen, >= 1 = absolute pixels.
- `window_options.multiInstance: true` allows multiple windows of the same plugin.

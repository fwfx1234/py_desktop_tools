# AGENTS.md
# 始终使用中文交互
# 系统是 macOS 开发环境，终端使用 zsh
# 项目使用 uv 管理依赖、虚拟环境和运行命令
# 使用 Codex 时，架构设计和执行计划优先由 5.5 模型完成，代码执行和落地修改优先由 5.4 模型完成

PySide6 + QML desktop toolbox with a uTools-like launcher. The app stays in the tray/background and is opened by global hotkeys such as `Alt+Space`.

## Commands

```bash
uv sync                              # sync dependencies into .venv
uv run app                           # run the app
uv run build                         # package the app via PyInstaller
uv add <pkg>                         # add a dependency
uv run pytest                        # run the configured test suite
uv run pytest tests/features/api_debugger # run the api-debugger focused tests
uv run python -m compileall src      # quick Python syntax check
```

QML hot reload:

```bash
PY_DESKTOP_QML_HOT_RELOAD=1 uv run app
```

Useful runtime env vars:
- `PY_DESKTOP_TOOLS_DATA_DIR` overrides startup/storage data directory.
- `PY_DESKTOP_TOOLS_PLUGIN_DIR` adds external plugin roots, separated by `os.pathsep`.
- `PY_DESKTOP_PLUGIN_RETENTION_MS` changes retained plugin-session timeout for debugging.
- `PY_DESKTOP_TOOLS_LOG_LEVEL` and `PY_DESKTOP_TOOLS_LOG_CONSOLE` control app logging.

PowerShell smoke scripts still exist under `scripts/`, but this repo is currently developed from macOS/zsh. Prefer the `uv run ...` commands above on macOS.

## Current Architecture

```
src/
  app/
    main.py                        # entry point: app.main:main
    app_runtime.py                 # Qt event-loop runtime and QML hot reload
    app_bootstrap.py               # QML engine, services, plugin managers, app services
    app_context.py                 # application lifecycle, startup scheduling, shutdown
    application_controller.py      # launcher and plugin lifecycle application use cases
    launcher/                      # launcher window, plugin host window, QML bridge
    commands/                      # command search/ranking, app index, dynamic commands
    plugins/                       # manifest loading, runtime loading, sessions, background plugins
    hotkeys/                       # global hotkey service and lifecycle
    platform/                      # PlatformServices and macos/windows/noop implementations
    services/                      # pure Python app-level services
    storage/                       # SQLite/dict storage helpers
    logging/                       # structured app and Qt logging
    concurrency/                   # background task runner
    tray/                          # system tray integration
    ui/                            # shared QML controls
    theme/                         # QML design tokens
  features/                        # bundled plugin packages
  tests/                           # pytest suite
```

Startup path:
- `src/app/main.py:main()` configures logging, Qt style, fonts and `QApplication`.
- `ApplicationRuntime.run()` builds the app, starts lifecycle hooks, optionally installs QML hot reload, then enters `qt_app.exec()`.
- `ApplicationBootstrapper.build()` creates `QQmlApplicationEngine`, injects global QML context, loads manifests, assembles platform services, command services, plugin managers, `ApplicationController`, `PluginHostService`, `HotkeyLifecycle`, and `TrayService`.
- `ApplicationContext.start()` connects launcher signals, schedules hotkey registration, starts background plugins, shows tray, and starts app-index refresh.

## Plugin System

- Bundled plugins live under `src/features/`; external plugins default to `plugins/` or `PY_DESKTOP_TOOLS_PLUGIN_DIR`.
- A plugin package can expose `plugin.json` or one or more `*.plugin.json` files.
- Manifest discovery is in `src/app/plugins/manifest_loader.py`; bundled manifests load before external manifests, and earlier duplicate plugin IDs win.
- `entrypoint: "runtime:create_runtime"` means module `runtime.py`, factory `create_runtime`. Feature-local relative imports are supported through synthetic package names in `PluginManager._import_module()`.
- Manifest `qmlPage` and local icon paths are resolved relative to the manifest package directory; `qta:` icons are passed through.
- Plugin IDs use kebab-case, Python packages/directories use snake_case, and QML components use PascalCase.

Supported command/manifest fields include:
- `activation`: `lazy` or `background`.
- `launchMode`: `none`, `list`, `inline_view`, or `window`.
- `inputMode`: `global` or `plugin`.
- `commands[].keywords`, `prefixes`, `hotkey`, `payload`.
- `commands[].matchers` with `source` `input`/`clipboard`, `kind`, `boost`, and optional `pattern`.
- `window.width`/`height`: values `< 1.0` are screen ratios; values `>= 1` are absolute pixels.
- `window.alwaysOnTop` and `window.fullscreen` are used by window hosting behavior when present.

## Runtime And Session Model

- Runtime loading is lazy through `PluginManager`; background plugin runtimes are not closed by `close_runtime()`.
- `PluginContext` gives runtimes access to command index/service, plugin-scoped platform API, and `ServiceRegistry`.
- `SimpleQmlRuntime` is the default helper for QML + ViewModel plugins and creates a `QmlPluginSession`.
- `PluginSessionManager` owns active and retained sessions and injects session context objects into the root QML context.
- Closing visible plugin UI usually suspends the session instead of destroying it. Retained sessions keep ViewModel/service state until the retention timer expires.
- `PluginHostService` owns inline/list/window host surfaces, independent plugin windows, native activation helpers, and destruction when retention expires.
- Plugins that need to clean up should expose `dispose()` on their ViewModel; `QmlPluginSession.close()` calls it before `deleteLater()`.
- `launchMode: "none"` commands execute and then unload immediately.

## Feature Layout

Preferred MVVM layout for feature plugins:

```
src/features/<feature>/
  plugin.json or *.plugin.json
  runtime.py
  view_model.py
  service.py
  <FeaturePage>.qml
  components/
```

Layering rules:
- Manifest declares commands, matching, launch mode, entrypoint, QML page, context property, and window options.
- `runtime.py` is the factory boundary from kernel to feature code.
- `view_model.py` is the only feature layer that should expose `QObject`, `Signal`, `Slot`, and `Property` to QML.
- `service.py`, repositories, parsers, transport, and state helpers should stay pure Python where practical.
- QML owns view composition, binding, and lightweight UI interaction only.
- QML files import shared components via `import "../../app/ui"` and `import "../../app/theme"` unless the existing file has a closer relative path.

## QML Context

Global QML context properties:
- `app` -> `AppViewModel`
- `launcherBridge` -> `LauncherBridge`

Plugin ViewModels are injected only while a session is active or retained. The property name comes from manifest `contextProperty`, for example `apiDebuggerVm`, `clipboardVm`, `jsonParserVm`, `qrVm`, or `systemSettingsVm`.

## Platform And Services

- Cross-platform SDK-style capabilities belong under `src/app/platform/`.
- `create_platform_services()` assembles `PlatformServices` from `macos/`, `windows/`, or `noop/` implementations plus common services.
- Keep OS-specific behavior under `src/app/platform/macos/`, `windows/`, `noop/`, or `common/`; do not add old flat platform modules.
- Plugins should use `ctx.platform` or `ctx.services` instead of importing OS-specific modules directly.
- Plugins own their own ViewModel/UI-thread callback handling; do not add a generic Qt adapter layer just to wrap Qt.

## Storage, Logging, And Data

- `StorageManager` owns app/plugin SQLite storage; startup data lives under `data/` unless `PY_DESKTOP_TOOLS_DATA_DIR` is set.
- Command indexing uses `CommandIndexDb` and is refreshed at startup and periodically in the background.
- Logging is structured through `app.logging`; app startup installs the Qt message handler.
- Avoid printing from runtime code unless it is intentionally part of a CLI/debug path.

## Testing

- Pytest is configured in `pyproject.toml` with `testpaths = ["tests"]` and `pythonpath = ["src"]`.
- Test markers include `unit`, `integration`, `contract`, and `slow`.
- Current focused coverage is strongest around `api_debugger`, core architecture, and app indexing.
- Do not add test files for GUI/plugin interaction changes; verify them by running `uv run app` and directly opening the affected plugins.
- For non-GUI pure Python logic changes, use existing focused tests when they already exist.
- At minimum run `uv run python -m compileall src` for code changes, then start the app and manually exercise affected launcher/plugin paths.

## Key Conventions

- Do not add code comments unless explicitly requested.
- Python runtime is pinned by `.python-version` to `3.13`; `pyproject.toml` currently declares `requires-python = ">=3.10"`.
- Dependencies and commands are managed by `uv`; the virtual env is `.venv`.
- `pyproject.toml` sets `where = ["src"]` for setuptools package discovery.
- Follow existing local style before introducing abstractions.
- Keep edits scoped; do not rewrite unrelated architecture or generated lock data unless the task requires it.
- Treat dirty git state as user work. Do not revert unrelated changes.

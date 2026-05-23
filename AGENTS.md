# AGENTS.md
# 始终使用中文交互
# 系统是 macOS 开发环境，终端使用 zsh
# 项目使用 uv 管理依赖、虚拟环境和运行命令

PySide6 + QML desktop toolbox with a uTools-like launcher. The app stays in the tray/background and is opened by global hotkeys such as `Alt+Space`.

**Repo moved from `fwfx1234/py_desktop_tools` → `fwfx1234/suishou`.**

## Commands

```bash
uv sync                              # sync dependencies into .venv
uv run app                           # run the app
uv add <pkg>                         # add a dependency
uv run pytest                        # run the configured test suite
uv run pytest tests/features/api_test # run the api-test focused tests
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

Build:
```bash
bash tools/build_macos.sh            # PyInstaller .app build
```

## Current Architecture

```
src/
  app/
    main.py                        # entry point: app.main:main
    app_runtime.py                 # Qt event-loop runtime and QML hot reload
    app_bootstrap.py               # QML engine, services, plugin managers, coordinators
    app_context.py                 # application lifecycle, startup scheduling, shutdown
    app_view_model.py              # global QML context (theme, platform info)
    app_relauncher.py              # self-restart (subprocess spawn)
    hotkey_coordinator.py          # launcher/clipboard/plugin hotkey lifecycle
    launcher_runtime_coordinator.py# launcher, plugin lifecycle signal wiring
    plugin_surface_coordinator.py  # inline/list/window plugin host surfaces
    tray_coordinator.py            # system tray coordinator
    paths.py                       # project/user_data/cache/plugin path resolution
    qta_icon_provider.py           # QtAwesome icon provider for QML
    version.py                     # app version
    launcher/                      # launcher window, plugin host window, QML bridge
    commands/                      # command search/ranking, app index, dynamic commands
    plugins/                       # manifest loading, runtime loading, sessions, background plugins
    platform/                      # PlatformServices and macos/windows/noop implementations
    platform/api.py                # PlatformApi — plugin-facing capability entry
    platform/factory.py            # platform service assembly
    platform/protocols.py          # platform capability protocols
    platform/services.py           # PlatformServices aggregate
    platform/models.py             # platform data models
    platform/screen.py             # screen info utilities
    platform/dialogs.py            # native dialog wrappers
    platform/common/               # cross-platform implementations
    platform/macos/                # macOS-specific implementations
    platform/windows/              # Windows-specific implementations
    platform/noop/                 # no-op stubs
    services/                      # pure Python app-level services
    services/clipboard/            # clipboard history service (listener, store, models)
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
- `ApplicationBootstrapper.build()` creates `QQmlApplicationEngine`, injects global QML context (`app`, `launcherBridge`), loads manifests, assembles platform services, command services, plugin managers, session/surface/runtime coordinators, hotkey coordinator, and tray coordinator.
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
- `PluginSurfaceCoordinator` owns inline/list/window host surfaces, independent plugin windows, macOS overlay activation helpers, and destruction when retention expires.
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
- `app` -> `AppViewModel` (theme mode, platform info)
- `launcherBridge` -> `LauncherBridge`

Plugin ViewModels are injected only while a session is active or retained. The property name comes from manifest `contextProperty`, for example `apiTestVm`, `clipboardVm`, `jsonParserVm`, `qrVm`, or `systemSettingsVm`.

## Platform And Services

- Cross-platform SDK-style capabilities belong under `src/app/platform/`.
- `PlatformServices` aggregates: platform info, hotkeys, app indexing, clipboard, dialogs, screen, storage, dynamic commands, permissions.
- Plugins use `ctx.platform` (a `PlatformApi`) instead of importing OS-specific modules directly.
- System commands go through an allowlist — plugins cannot execute arbitrary shell commands.
- `ServiceRegistry` provides cross-plugin services like clipboard listener/history.

## Storage, Logging, And Data

- `StorageManager` owns app/plugin SQLite storage; startup data lives under `data/` unless `PY_DESKTOP_TOOLS_DATA_DIR` is set.
- Command indexing uses `CommandIndexDb` and is refreshed at startup and periodically in the background.
- Logging is structured through `app.logging`; app startup installs the Qt message handler.
- Path resolution via `app.paths`: `project_root()`, `resource_root()`, `user_data_dir()`, `cache_dir()`, `plugin_dirs()`.
- Avoid printing from runtime code unless it is intentionally part of a CLI/debug path.

## Testing

- Pytest is configured in `pyproject.toml` with `testpaths = ["tests"]` and `pythonpath = ["src"]`.
- Test markers include `unit`, `integration`, `contract`, and `slow`.

## Bundle Features

| Feature | Type | Description |
|---------|------|-------------|
| `api_test` | inline_view/window | HTTP/WebSocket/Mock API testing tool |
| `app_launcher` | list | System application index |
| `clipboard` | background+window | Clipboard history with listener |
| `download` | inline_view | Download manager |
| `image_compress` | inline_view | Image compression tool |
| `json_parser` | inline_view | JSON format/validate/minify |
| `packet_capture` | window | Network capture (demo/WIP) |
| `qml_demo` | inline_view | QML learning demos (17 pages) |
| `qr` | inline_view | QR code generate/scan |
| `quick_launch` | inline_view | Fast project/script launcher |
| `remote_files` | window | Remote file manager (SSH/SFTP + xterm terminal) |
| `system` | inline_view | Settings + About pages |

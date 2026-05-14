## py-desktop-tools (QML Edition)

Desktop toolbox built with `PySide6 + Qt Quick (QML)` using an MVVM + feature-first architecture.

### Learning guide

如果你是 PyQt/PySide6 + QML 新手，请先读：

- [PyQt/PySide6 + QML 新手教程：读懂并掌握本项目](docs/pyqt-qml-newbie-guide.zh-CN.md)
- [插件开发文档](docs/plugin-development.zh-CN.md)
- [类 uTools 架构设计文档](docs/utools-like-architecture.zh-CN.md)

### Architecture

```
src/
  app/
    main.py            # entry point, wires the app kernel, launcher, commands, plugins
    Main.qml           # application shell, loads the launcher window
    app_view_model.py  # global app state (theme, etc.)
    launcher/          # Alt+Space launcher window and plugin window shell
    commands/          # search, ranking, system commands, app shortcut index
    plugins/           # manifest loading, runtime loading, sessions, background plugins
    hotkey/            # Windows global hotkeys
    tray/              # system tray
    ui/                # shared QML controls
  features/
    api_test/
      plugin.json          # Manifest: commands, entrypoint, launch mode
      runtime.py           # Runtime: creates sessions/ViewModels lazily
      ApiTestPage.qml      # View
      view_model.py        # ViewModel (QObject, exposes Property/Signal/Slot)
      service.py           # Service (pure business logic)
    download/        ...
    image_compress/  ...
    json_parser/     ...
    packet_capture/  ...
    qr/              ...
    system/              # view-only pages (settings, about) bound to AppViewModel
```

### Layering

- Manifest (`plugin.json`) declares commands, matching rules, launch mode, QML page, and runtime entrypoint.
- Runtime is loaded lazily when a plugin is launched, except `background` plugins such as clipboard history.
- Session owns one plugin launch and injects temporary QML context objects.
- View (QML) renders and binds to its feature's ViewModel.
- ViewModel (`QObject`) exposes `Property`, `Signal`, `Slot` for QML and orchestrates the Service.
- Service is plain Python with no QML dependency, easier to test.

### QML context properties

Global QML context properties are injected in `src/app/main.py`:

| Property | ViewModel |
|----------|-----------|
| `app` | `AppViewModel` |
| `launcherBridge` | `LauncherBridge` |

Plugin ViewModels are injected only while a plugin session is active, using the plugin manifest's `contextProperty`, for example `jsonParserVm`, `qrVm`, `clipboardVm`, or `apiTestVm`.

### Run

```bash
uv run app
```

Or via the installed entry point:

```bash
app
```

# 跨平台插件能力层设计：参考 uTools SDK

本文用于指导低级模型继续扩展当前项目的平台层。目标不是复刻完整 uTools SDK，而是参考 uTools 给插件提供系统能力的方式，为当前 PySide6 + QML 桌面工具箱设计一组稳定、跨平台、可逐步实现的插件 API。

当前已有 `src/app/platform/` 基础层，插件可以通过 `ctx.platform` 获取 `PlatformApi`。本文在这个基础上继续扩展能力边界。

## 背景

uTools 插件 SDK 的价值不在于某一个具体 API，而在于它把系统能力收口为受控入口，让插件不需要直接面对 Windows/macOS 差异。它覆盖的能力大致包括：

- 插件进入、退出、窗口显示和隐藏。
- 主输入框、子输入框、动态功能入口。
- 系统路径、文件打开、URL 打开、通知、对话框。
- 剪贴板复制文本、图片、文件，以及自动粘贴。
- 屏幕、显示器、截图、取色。
- 本地数据库和键值存储。
- 键盘、鼠标模拟。

当前项目已有自己的插件生命周期、Launcher、QML 窗口和存储模块，因此不能照搬 uTools API 命名和行为。应该抽取适合本项目的能力，并封装为 Python 插件 API。

参考资料：

- uTools 开发者文档总览：[https://www.u-tools.cn/docs/developer/docs.html](https://www.u-tools.cn/docs/developer/docs.html)
- uTools 窗口 API：[https://www.u-tools.cn/docs/developer/api-reference/utools/window.html](https://www.u-tools.cn/docs/developer/api-reference/utools/window.html)
- uTools 系统 API：[https://www.u-tools.cn/docs/developer/api-reference/utools/system.html](https://www.u-tools.cn/docs/developer/api-reference/utools/system.html)
- uTools 屏幕 API：[https://www.u-tools.cn/docs/developer/api-reference/utools/screen.html](https://www.u-tools.cn/docs/developer/api-reference/utools/screen.html)

## 设计目标

- 插件只通过 `ctx.platform` 使用系统能力。
- 平台差异集中在 `src/app/platform/`，插件不直接 import Windows/macOS 实现。
- 公开 API 返回结构化结果，普通系统失败不抛异常。
- 优先实现能稳定跨平台的能力：路径、打开、剪贴板、对话框、屏幕信息、存储、动态命令。
- 延后实现需要权限或焦点语义的能力：模拟按键、自动粘贴、全局鼠标键盘监听、当前浏览器 URL。
- 低级模型必须按文档顺序小步实现，每步都能 `compileall`。

## 非目标

- 不改造成 Electron 插件模型。
- 不把 JavaScript SDK 直接暴露给插件。
- 不允许插件直接注册任意全局热键。
- 不做 macOS 签名、公证、权限引导 UI。
- 不实现 uTools 的全部窗口 API，例如 `setSubInput`、`setExpendHeight`。
- 不在第一阶段实现截图、取色、自动粘贴和模拟输入。

## 总体架构

保持双层结构：

- `PlatformServices`：内核私有，持有各类底层服务对象。
- `PlatformApi`：插件公开入口，只暴露稳定方法。

扩展后目录建议：

```text
src/app/platform/
  api.py
  models.py
  services.py
  factory.py
  external_launcher.py
  system_commands.py
  clipboard.py
  dialogs.py
  screen.py
  storage.py
  dynamic_commands.py
  permissions.py
  apps_windows.py
  apps_macos.py
  apps_noop.py
  hotkey_windows.py
  hotkey_macos.py
  hotkey_noop.py
```

其中：

- `external_launcher.py` 继续负责打开应用、文件、目录、URL。
- `clipboard.py` 负责当前系统剪贴板读写，不负责剪贴板历史。
- `dialogs.py` 负责系统打开/保存文件对话框。
- `screen.py` 负责显示器和光标所在屏幕信息。
- `storage.py` 包装现有 `app.storage.StorageManager`，给插件提供命名空间存储。
- `dynamic_commands.py` 包装 `DynamicCommandRegistry`，让插件以更窄接口注册动态命令。
- `permissions.py` 只返回权限状态或说明，不做自动授权。

## 能力分层

### 第一阶段必须实现

这些能力稳定、风险低，适合作为 `PlatformApi` 的第一批扩展：

| 能力 | 插件 API | 底层实现 |
|---|---|---|
| 平台信息 | `platform.info` | 已有 |
| 用户路径 | `user_data_dir()`、`cache_dir()`、`resource_root()` | 已有 |
| 文件/URL 打开 | `open_path()`、`reveal_in_file_manager()`、`open_url()` | 已有，需补协议 |
| 应用扫描/启动 | `scan_applications()`、`launch_application()` | 已有 |
| 系统命令 | `system_commands()`、`run_system_action()` | 已有 |
| 剪贴板读写 | `clipboard.read_text()`、`clipboard.write_text()`、`clipboard.write_files()` | 新增 |
| 系统对话框 | `dialogs.open_file()`、`dialogs.open_files()`、`dialogs.open_directory()`、`dialogs.save_file()` | 新增 |
| 屏幕信息 | `screen.primary_display()`、`screen.all_displays()`、`screen.cursor_position()`、`screen.display_at_cursor()` | 新增 |
| 插件存储 | `storage.for_plugin(plugin_id)` | 新增包装 |
| 动态命令 | `commands.register()`、`commands.unregister()`、`commands.unregister_plugin()` | 新增包装 |

### 第二阶段再实现

这些能力可做，但要等第一阶段稳定后再做：

| 能力 | 原因 |
|---|---|
| `clipboard.write_image()` | 需要统一 image path、QImage 和 QML URL 的边界 |
| `clipboard.read_files()` | 各平台文件剪贴板格式略有差异 |
| `window.hide_launcher()`、`window.show_launcher()` | 需要在主入口注入窗口控制器 |
| `screen.capture()` | macOS 屏幕录制权限和截图 API 差异明显 |
| `screen.pick_color()` | 需要交互式取色 UI 或系统 API |
| `input.paste_text()` | 需要焦点恢复和辅助功能权限 |
| `input.simulate_key()` | macOS 需要辅助功能权限，Windows 也有安全边界 |
| `system.current_browser_url()` | 浏览器差异大，可靠性不足 |
| `system.current_folder()` | Windows Explorer/Finder 当前路径获取差异大 |

### 第一阶段明确不做

- 插件任意注册全局热键。
- 插件监听全局键盘或鼠标。
- 插件控制其他应用窗口置顶、移动、透明、穿透。
- 插件直接执行任意 shell 命令。
- 插件直接读取底层服务对象，例如 `platform._services`。

## 公开模型设计

在 `src/app/platform/models.py` 中新增这些模型。

```python
from dataclasses import dataclass, field
from typing import Any, Literal


PlatformName = Literal["windows", "macos", "unknown"]
DisplayId = str


@dataclass(frozen=True, slots=True)
class PlatformResult:
    ok: bool
    message: str = ""
    code: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FileDialogFilter:
    name: str
    patterns: list[str] = field(default_factory=list)

    def to_qt_filter(self) -> str:
        pattern_text = " ".join(self.patterns) if self.patterns else "*"
        return f"{self.name} ({pattern_text})"


@dataclass(frozen=True, slots=True)
class FileDialogOptions:
    title: str = ""
    directory: str = ""
    filters: list[FileDialogFilter] = field(default_factory=list)
    default_name: str = ""


@dataclass(frozen=True, slots=True)
class DisplayInfo:
    id: DisplayId
    name: str
    x: int
    y: int
    width: int
    height: int
    available_x: int
    available_y: int
    available_width: int
    available_height: int
    scale_factor: float = 1.0
    is_primary: bool = False


@dataclass(frozen=True, slots=True)
class CursorPosition:
    x: int
    y: int
```

低级模型注意：

- 已有 `PlatformInfo`、`AppEntry`、`SystemCommand` 不要删除。
- 新模型只追加，不破坏现有 import。
- `FileDialogFilter.to_qt_filter()` 可以放在模型中，因为它不依赖 Qt import。

## `PlatformServices` 扩展

修改 `src/app/platform/services.py`：

```python
@dataclass(slots=True)
class PlatformServices:
    info: PlatformInfo
    default_launcher_hotkey: str
    default_clipboard_hotkey: str
    paths: object
    hotkey_factory: object
    app_indexer: object
    external_launcher: object
    system_commands: object
    clipboard: object
    dialogs: object
    screen: object
    storage_factory: object
    dynamic_command_api_factory: object
    permissions: object

    def create_api(self, *, plugin_id: str = "") -> PlatformApi:
        return PlatformApi(self, plugin_id=plugin_id)
```

重要约定：

- `create_api(plugin_id="")` 默认创建内核级 API。
- 插件 Session 里推荐使用带 `plugin_id` 的 API，保证存储和动态命令能自动归属。
- 低级模型可以先让 `PlatformApi` 接收 `plugin_id`，但现有 `main.py` 继续用 `create_api()`，不要一次性改动所有调用点。

## 插件专属 `PlatformApi`

当前所有插件共用一个 `platform_api`。为了存储和动态命令归属清晰，需要增加“按插件创建 API”的能力。

推荐实现：

1. `PlatformApi.__init__(services, plugin_id="")` 保存 `_plugin_id`。
2. `PlatformApi.for_plugin(plugin_id)` 返回新的 `PlatformApi(self._services, plugin_id=plugin_id)`。
3. `PluginSessionManager.open_plugin()` 调用 runtime 前，临时替换 `PluginContext.platform` 为插件专属 API。
4. 调用结束后恢复原来的 `PluginContext.platform`。

实现示例：

```python
def open_plugin(...):
    old_platform = self._plugin_context.platform
    base_platform = old_platform
    if base_platform is not None and hasattr(base_platform, "for_plugin"):
        self._plugin_context.platform = base_platform.for_plugin(plugin_id)
    try:
        session = self._plugin_manager.open_session(...)
    finally:
        self._plugin_context.platform = old_platform
```

后台插件同理：

- `BackgroundManager.start_all()` 在调用 `on_background_start(ctx)` 前也要临时注入 `platform.for_plugin(manifest.id)`。
- 调用后恢复。

注意：

- `ctx.services["platform"]` 是兼容入口，可以继续指向基础 API。
- 新插件只用 `ctx.platform`。
- 不要在 `PluginContext` 中为每个插件复制整个 `services` dict。

## `PlatformApi` 方法清单

修改 `src/app/platform/api.py`，最终公开方法建议如下。

```python
class PlatformApi:
    @property
    def info(self) -> PlatformInfo: ...

    @property
    def clipboard(self) -> ClipboardApi: ...

    @property
    def dialogs(self) -> DialogApi: ...

    @property
    def screen(self) -> ScreenApi: ...

    @property
    def storage(self) -> PluginStorageApi: ...

    @property
    def commands(self) -> PluginCommandApi: ...

    @property
    def permissions(self) -> PermissionApi: ...

    def for_plugin(self, plugin_id: str) -> PlatformApi: ...
    def is_windows(self) -> bool: ...
    def is_macos(self) -> bool: ...
    def user_data_dir(self) -> Path: ...
    def cache_dir(self) -> Path: ...
    def resource_root(self) -> Path: ...
    def plugin_data_dir(self) -> Path: ...
    def plugin_cache_dir(self) -> Path: ...
    def scan_applications(self) -> list[AppEntry]: ...
    def system_commands(self) -> list[SystemCommand]: ...
    def open_path(self, path: str | Path) -> PlatformResult: ...
    def reveal_in_file_manager(self, path: str | Path) -> PlatformResult: ...
    def open_url(self, url: str) -> PlatformResult: ...
    def launch_application(self, app: AppEntry | dict) -> PlatformResult: ...
    def run_system_action(self, action: str) -> PlatformResult: ...
```

命名原则：

- 子能力使用名词属性：`platform.clipboard.write_text(...)`。
- 顶层保留高频通用方法：`open_path()`、`open_url()`、`launch_application()`。
- 不使用 uTools 的驼峰命名，Python 侧统一 snake_case。

## 剪贴板能力

新增 `src/app/platform/clipboard.py`。

### 公开接口

```python
class ClipboardApi:
    def read_text(self) -> str: ...
    def write_text(self, text: str) -> PlatformResult: ...
    def clear(self) -> PlatformResult: ...
    def write_files(self, paths: list[str | Path]) -> PlatformResult: ...
```

第二阶段再加：

```python
def read_files(self) -> list[Path]: ...
def write_image(self, path: str | Path) -> PlatformResult: ...
```

### Qt 实现

第一阶段用 Qt 实现即可跨平台：

```python
from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtWidgets import QApplication


class QtClipboardApi:
    def read_text(self) -> str:
        clipboard = QApplication.clipboard()
        return clipboard.text() if clipboard is not None else ""

    def write_text(self, text: str) -> PlatformResult:
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return PlatformResult(False, "剪贴板不可用", "unavailable")
        clipboard.setText(text)
        return PlatformResult(True, data={"type": "text"})

    def clear(self) -> PlatformResult:
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return PlatformResult(False, "剪贴板不可用", "unavailable")
        clipboard.clear()
        return PlatformResult(True)

    def write_files(self, paths: list[str | Path]) -> PlatformResult:
        clean_paths = [Path(path) for path in paths if str(path)]
        missing = [str(path) for path in clean_paths if not path.exists()]
        if missing:
            return PlatformResult(False, "文件不存在", "not_found", {"missing": missing})
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(path)) for path in clean_paths])
        QApplication.clipboard().setMimeData(mime)
        return PlatformResult(True, data={"count": len(clean_paths)})
```

注意：

- 这里是“系统剪贴板当前内容”，不是剪贴板历史插件。
- 剪贴板历史插件可以继续使用自己的 `ClipboardBackgroundService`。
- 后续可以让剪贴板历史插件内部改用 `ctx.platform.clipboard` 写回内容。

## 对话框能力

新增 `src/app/platform/dialogs.py`。

### 公开接口

```python
class DialogApi:
    def open_file(self, options: FileDialogOptions | None = None) -> Path | None: ...
    def open_files(self, options: FileDialogOptions | None = None) -> list[Path]: ...
    def open_directory(self, options: FileDialogOptions | None = None) -> Path | None: ...
    def save_file(self, options: FileDialogOptions | None = None) -> Path | None: ...
```

### Qt 实现

使用 `QFileDialog`，不要直接用 Windows/macOS 原生命令。

```python
from PySide6.QtWidgets import QFileDialog


class QtDialogApi:
    def open_file(self, options: FileDialogOptions | None = None) -> Path | None:
        opts = options or FileDialogOptions()
        path, _ = QFileDialog.getOpenFileName(
            None,
            opts.title,
            opts.directory,
            _qt_filters(opts),
        )
        return Path(path) if path else None
```

约定：

- 用户取消返回 `None` 或空列表，不返回失败 result。
- 打开文件对话框不应写日志警告，取消是正常行为。
- `filters` 使用 `FileDialogFilter`。

插件示例：

```python
path = platform.dialogs.open_file(
    FileDialogOptions(
        title="选择图片",
        filters=[FileDialogFilter("Images", ["*.png", "*.jpg", "*.webp"])],
    )
)
```

## 屏幕能力

新增 `src/app/platform/screen.py`。

### 公开接口

```python
class ScreenApi:
    def primary_display(self) -> DisplayInfo | None: ...
    def all_displays(self) -> list[DisplayInfo]: ...
    def cursor_position(self) -> CursorPosition: ...
    def display_at_cursor(self) -> DisplayInfo | None: ...
```

### Qt 实现

使用 `QGuiApplication.screens()` 和 `QCursor.pos()`。

```python
from PySide6.QtGui import QCursor, QGuiApplication


class QtScreenApi:
    def all_displays(self) -> list[DisplayInfo]:
        primary = QGuiApplication.primaryScreen()
        return [_to_display_info(screen, screen is primary) for screen in QGuiApplication.screens()]
```

`DisplayInfo.id` 可以先使用：

```python
f"{screen.name()}:{geometry.x()}:{geometry.y()}:{geometry.width()}:{geometry.height()}"
```

注意：

- 不要在第一阶段做截图。
- 不要在第一阶段做取色。
- 插件需要窗口定位时应读屏幕信息，但真正移动窗口仍由内核控制。

## 插件存储能力

已有 `src/app/storage/`，不要另造一套数据库。平台层只做更窄包装。

新增 `src/app/platform/storage.py`。

### 公开接口

```python
class PlatformStorageFactory:
    def __init__(self, storage_manager: StorageManager) -> None: ...
    def for_plugin(self, plugin_id: str) -> PluginStorageApi: ...


class PluginStorageApi:
    def path(self, name: str | Path) -> Path: ...
    def cache_path(self, name: str | Path) -> Path: ...
    def dict_store(self, namespace: str = "settings", defaults: dict | None = None) -> JsonDictStore: ...
    def database(self, name: str = "plugin.db", **kwargs) -> SQLiteDatabase: ...
```

路径规则：

```text
<user_data_dir>/plugins/<plugin_id>/
<user_data_dir>/cache/plugins/<plugin_id>/
```

安全规则：

- `plugin_id` 必须经过安全化处理，只允许字母、数字、`_`、`-`、`.`。
- `path(name)` 如果传入绝对路径，第一阶段应拒绝，返回插件目录下路径或抛 `ValueError`。
- 不允许 `..` 逃出插件目录。

推荐辅助函数：

```python
def _safe_plugin_id(plugin_id: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_.-]+", "_", plugin_id.strip())
    return value.strip("._") or "anonymous"
```

插件示例：

```python
store = ctx.platform.storage.dict_store("settings", defaults={"enabled": True})
store.set("enabled", False)

db = ctx.platform.storage.database("records.db", row_factory=SQLiteRow)
```

注意：

- `ctx.services["storage"]` 可以继续存在，供旧插件使用。
- 新插件优先使用 `ctx.platform.storage`。
- 不要暴露全局 `StorageManager.root` 给插件修改。

## 动态命令能力

当前插件可直接拿 `ctx.dynamic_commands`，但这个对象是内核实现细节。需要包装为插件专属 API。

新增 `src/app/platform/dynamic_commands.py`。

### 公开接口

```python
class PlatformCommandApiFactory:
    def __init__(self, registry: DynamicCommandRegistry | None) -> None: ...
    def for_plugin(self, plugin_id: str) -> PluginCommandApi: ...


class PluginCommandApi:
    def register(
        self,
        command_id: str,
        *,
        title: str,
        subtitle: str = "",
        icon: str = "",
        keywords: list[str] | None = None,
        prefixes: list[str] | None = None,
        launch_mode: LaunchMode = "none",
        payload: dict | None = None,
        order: int = 500,
    ) -> PlatformResult: ...

    def unregister(self, command_id: str) -> PlatformResult: ...
    def unregister_all(self) -> PlatformResult: ...
```

实现规则：

- `plugin_id` 从 `PlatformApi` 注入，插件不能伪造别的插件 ID。
- `command_id` 如果不含插件前缀也允许，底层仍用 `(plugin_id, command_id)` 存储。
- `register()` 内部构造 `DynamicCommand`。
- `registry` 为 `None` 时返回 `unsupported`，不要抛异常。

插件示例：

```python
ctx.platform.commands.register(
    "recent.open.1",
    title="打开最近请求",
    subtitle="GET https://example.com",
    icon="qta:mdi6.history",
    launch_mode="window",
    payload={"requestId": 1},
    order=80,
)
```

清理规则：

- 非后台插件 Session 关闭时不自动清理动态命令。
- 插件 Runtime 的 `on_exit()` 或后台停止时应主动 `unregister_all()`。
- 后续可以在 `PluginManager.close_runtime()` 中统一清理，但第一阶段先不做隐式行为。

## 权限能力

新增 `src/app/platform/permissions.py`。

### 公开接口

```python
class PermissionApi:
    def accessibility_status(self) -> PlatformResult: ...
    def screen_recording_status(self) -> PlatformResult: ...
```

第一阶段实现：

- Windows 返回 `PlatformResult(True, data={"status": "not_required"})`。
- unknown 返回 `unsupported`。
- macOS 可以先返回 `unknown`，不要尝试弹系统授权。

示例返回：

```python
PlatformResult(True, data={"status": "unknown", "platform": "macos"})
```

状态枚举建议：

```text
granted
denied
unknown
not_required
unsupported
```

后续如果实现真实 macOS 权限检测，也只能放在 `permissions_macos.py` 或 `permissions.py` 的 macOS 分支中，不要让插件自己调 AppleScript。

## 系统和打开能力补强

现有 `PlatformApi` 已有：

- `open_path()`
- `reveal_in_file_manager()`
- `open_url()`
- `launch_application()`
- `run_system_action()`

低级模型需要补强以下点：

1. `open_path()` 对不存在路径返回 `not_found`。
2. `open_url()` 对空字符串返回 `invalid`。
3. `launch_system_action()` 不再接受任意插件传来的 shell 字符串。

### 系统动作安全约束

当前系统命令使用 `action` 字符串，例如 `open -a Terminal` 或 `cmd.exe`。为了避免插件传任意命令，新增一种更安全的执行方式：

```python
class SystemCommand:
    id: str
    action: str
```

保留数据结构不变，但 `run_system_action(action)` 只允许执行 `system_commands()` 返回列表中的 action，或者内核保留动作 `__restart_app__`。

实现方式：

```python
def run_system_action(self, action: str) -> PlatformResult:
    allowed = {command.action for command in self.system_commands()}
    if action not in allowed:
        return PlatformResult(False, "系统动作不在允许列表中", "forbidden")
    return self._services.external_launcher.launch_system_action(action)
```

注意：

- `CommandService` 是内核，可以继续调用底层 `external_launcher.launch_system_action()`。
- 插件公开 API 必须走允许列表。

## 工厂注入设计

修改 `src/app/platform/factory.py`。

每个平台都需要提供：

```python
clipboard=QtClipboardApi()
dialogs=QtDialogApi()
screen=QtScreenApi()
storage_factory=PlatformStorageFactory(StorageManager())
dynamic_command_api_factory=PlatformCommandApiFactory(None)
permissions=...
```

但 `dynamic_command_api_factory` 需要拿到 `DynamicCommandRegistry`，而 registry 在 `main.py` 中创建。不要在 `factory.py` 里创建 registry。

推荐做法：

1. `create_platform_services(app)` 中先把 `dynamic_command_api_factory` 设为 `PlatformCommandApiFactory(None)`。
2. 在 `main.py` 创建 `dynamic_commands` 后，调用：

```python
platform_services.dynamic_command_api_factory.set_registry(dynamic_commands)
```

或者更简单：

```python
platform_services.dynamic_command_api_factory = PlatformCommandApiFactory(dynamic_commands)
platform_api = platform_services.create_api()
```

因为 `PlatformServices` 是 dataclass，不是 frozen，可以在 `main.py` 里赋值。低级模型优先选第二种，改动少。

同理，`storage_factory` 可以在 `factory.py` 中创建，也可以复用 `main.py` 的 `storage = StorageManager()`。为了避免两个 StorageManager 指向不同 root，推荐：

```python
storage = StorageManager()
platform_services.storage_factory = PlatformStorageFactory(storage)
plugin_context.services = {"platform": platform_api, "storage": storage}
```

注意顺序：

1. 创建 `platform_services`。
2. 创建 `storage` 和 `dynamic_commands`。
3. 写入 `platform_services.storage_factory` 和 `platform_services.dynamic_command_api_factory`。
4. 再创建 `platform_api = platform_services.create_api()`。

如果现有代码已经先创建 `platform_api`，也可让 `PlatformApi` 动态读取 services，不缓存子 API。但为插件专属 API 更清晰，建议先调整顺序。

## no-op 实现

所有新增子能力都需要 no-op 或 Qt 通用实现。

建议：

- `QtClipboardApi`、`QtDialogApi`、`QtScreenApi` 跨 Windows/macOS/unknown 都可用。
- `NoopPermissionApi` 用于 unknown。
- `PlatformStorageFactory` 跨平台可用。
- `PlatformCommandApiFactory(None)` 跨平台可用，但 register 返回 `unsupported`。

不要出现 unknown 平台 import 崩溃。

## 插件开发规范更新

修改 `docs/plugin-development.zh-CN.md` 的 `PluginContext` 小节。

新增推荐：

```python
def on_enter(self, ctx: PluginContext, action: PluginAction):
    platform = ctx.platform
    if platform is None:
        raise RuntimeError("Platform API is unavailable")

    settings = platform.storage.dict_store("settings")
    copied = platform.clipboard.read_text()
```

新增禁止：

```python
QApplication.clipboard()
QFileDialog.getOpenFileName(...)
os.startfile(...)
subprocess.Popen(["open", ...])
ctx.dynamic_commands.register(...)
StorageManager()
```

例外：

- 剪贴板历史插件作为后台服务可以继续直接监听 `QApplication.clipboard()`，因为它本身就是剪贴板底层服务。
- 旧插件可暂时保留 `ctx.services`，但新能力不要再加到 `ctx.services` 中。

## 实施顺序

低级模型必须按顺序执行。

### 第 1 步：追加模型

文件：

```text
src/app/platform/models.py
```

操作：

- 追加 `FileDialogFilter`。
- 追加 `FileDialogOptions`。
- 追加 `DisplayInfo`。
- 追加 `CursorPosition`。

验证：

```powershell
python -m compileall src/app/platform
```

### 第 2 步：新增剪贴板、对话框、屏幕实现

文件：

```text
src/app/platform/clipboard.py
src/app/platform/dialogs.py
src/app/platform/screen.py
```

操作：

- 实现 `QtClipboardApi`。
- 实现 `QtDialogApi`。
- 实现 `QtScreenApi`。
- 所有失败返回 `PlatformResult`，用户取消文件对话框返回 `None` 或 `[]`。

验证：

```powershell
python -m compileall src/app/platform
```

### 第 3 步：新增插件存储包装

文件：

```text
src/app/platform/storage.py
```

操作：

- 实现 `PlatformStorageFactory`。
- 实现 `PluginStorageApi`。
- 做路径安全检查，禁止 `..` 逃逸插件目录。

验证：

```powershell
python -m compileall src/app/platform
```

### 第 4 步：新增动态命令包装

文件：

```text
src/app/platform/dynamic_commands.py
```

操作：

- 实现 `PlatformCommandApiFactory`。
- 实现 `PluginCommandApi`。
- `registry is None` 时返回 `unsupported`。

验证：

```powershell
python -m compileall src/app/platform src/app/commands
```

### 第 5 步：新增权限包装

文件：

```text
src/app/platform/permissions.py
```

操作：

- 实现 `PermissionApi` 或 `DefaultPermissionApi`。
- Windows 返回 `not_required`。
- macOS 第一阶段返回 `unknown`。
- unknown 返回 `unsupported`。

验证：

```powershell
python -m compileall src/app/platform
```

### 第 6 步：扩展 `PlatformServices`

文件：

```text
src/app/platform/services.py
```

操作：

- 追加 `clipboard`、`dialogs`、`screen`、`storage_factory`、`dynamic_command_api_factory`、`permissions` 字段。
- `create_api()` 增加 `plugin_id` 参数。

注意：

- 这一步会要求 `factory.py` 同时补齐字段，否则 import 会失败。

### 第 7 步：扩展 `factory.py`

文件：

```text
src/app/platform/factory.py
```

操作：

- 懒导入平台相关实现的原则不变。
- 顶层可以导入 Qt 通用实现：`QtClipboardApi`、`QtDialogApi`、`QtScreenApi`。
- Windows/macOS 分支和 unknown 分支都要传入新增字段。

注意：

- 不要把 `apps_windows.py` 或 `hotkey_windows.py` 移到顶层 import。
- `ctypes.windll` 仍只能在 Windows 分支下 import 到。

### 第 8 步：扩展 `PlatformApi`

文件：

```text
src/app/platform/api.py
```

操作：

- `__init__` 增加 `plugin_id`。
- 新增 `for_plugin(plugin_id)`。
- 新增 `clipboard`、`dialogs`、`screen`、`storage`、`commands`、`permissions` 属性。
- 新增 `plugin_data_dir()`、`plugin_cache_dir()`。
- 修改 `run_system_action()`，只允许执行平台命令列表中存在的 action。

注意：

- `storage` 和 `commands` 应按当前 `_plugin_id` 返回插件专属 API。
- `_plugin_id` 为空时，`plugin_data_dir()` 使用 `anonymous` 或返回全局目录都可以，但推荐 `anonymous`，避免写根目录。

### 第 9 步：调整 `main.py` 注入顺序

文件：

```text
src/app/main.py
```

操作：

- 创建 `platform_services` 后，先创建 `storage`、`dynamic_commands`。
- 把 `storage_factory` 和 `dynamic_command_api_factory` 注入 `platform_services`。
- 再创建 `platform_api`。
- 保持 `plugin_context.services["storage"]` 兼容旧插件。

推荐顺序：

```python
platform_services = create_platform_services(qt_app)
storage = StorageManager()
dynamic_commands = DynamicCommandRegistry()
platform_services.storage_factory = PlatformStorageFactory(storage)
platform_services.dynamic_command_api_factory = PlatformCommandApiFactory(dynamic_commands)
platform_api = platform_services.create_api()
```

### 第 10 步：为插件注入专属 API

文件：

```text
src/app/plugins/session_manager.py
src/app/plugins/background_manager.py
```

操作：

- 调用插件 runtime 前，把 `ctx.platform` 临时替换为 `ctx.platform.for_plugin(plugin_id)`。
- 调用结束后恢复。
- 异常时也必须恢复，使用 `try/finally`。

验证：

```powershell
python -m compileall src/app/plugins src/app/platform
```

### 第 11 步：更新插件开发文档

文件：

```text
docs/plugin-development.zh-CN.md
```

操作：

- 更新 `PluginContext` 字段表，加入 `ctx.platform`。
- 增加平台能力示例。
- 标记 `ctx.dynamic_commands` 为兼容入口，新插件推荐 `ctx.platform.commands`。
- 标记 `ctx.services["storage"]` 为兼容入口，新插件推荐 `ctx.platform.storage`。

### 第 12 步：全量静态验证

命令：

```powershell
python -m compileall src
python -c "import sys; sys.path.insert(0, 'src'); import app.main; print('IMPORT_OK')"
```

如果本机只能通过 `.venv` 执行：

```powershell
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); import app.main; print('IMPORT_OK')"
```

## 代码示例：插件使用方式

### 打开文件

```python
from app.platform.models import FileDialogFilter, FileDialogOptions


path = ctx.platform.dialogs.open_file(
    FileDialogOptions(
        title="选择 JSON 文件",
        filters=[FileDialogFilter("JSON", ["*.json"])],
    )
)
if path is not None:
    text = path.read_text(encoding="utf-8")
```

### 写入剪贴板

```python
result = ctx.platform.clipboard.write_text("hello")
if not result.ok:
    print(f"[WARN] 写入剪贴板失败: {result.code} {result.message}")
```

### 使用插件存储

```python
settings = ctx.platform.storage.dict_store("settings", defaults={"theme": "system"})
settings.set("theme", "dark")
db = ctx.platform.storage.database("data.db")
```

### 注册动态命令

```python
ctx.platform.commands.register(
    "open-latest",
    title="打开最近记录",
    subtitle="来自当前插件",
    icon="qta:mdi6.history",
    launch_mode="window",
    payload={"source": "latest"},
)
```

### 读取屏幕信息

```python
display = ctx.platform.screen.display_at_cursor()
if display is not None:
    print(display.available_width, display.available_height)
```

## 验收清单

低级模型完成后必须满足：

- `python -m compileall src` 通过。
- `import app.main` 不触发 Windows-only import 错误。
- Windows 上 `Alt+Space`、应用启动器、剪贴板插件不回退。
- macOS 上仍不 import `ctypes.windll`。
- 插件可通过 `ctx.platform.clipboard.write_text()` 写入剪贴板。
- 插件可通过 `ctx.platform.dialogs.open_file()` 打开系统文件对话框。
- 插件可通过 `ctx.platform.screen.all_displays()` 获取显示器列表。
- 插件可通过 `ctx.platform.storage.dict_store()` 写入插件独立目录。
- 插件可通过 `ctx.platform.commands.register()` 注册动态命令，并且命令归属当前插件。
- `ctx.services["platform"]` 兼容入口仍存在。
- 新增能力在 unknown 平台不崩溃，无法支持时返回 `unsupported`。

## 常见错误

- 把 `apps_windows.py` 放到 `factory.py` 顶层 import，导致 macOS import 崩溃。
- 在插件里直接使用 `QFileDialog` 或 `QApplication.clipboard()`，导致平台能力绕过统一入口。
- `PluginStorageApi.path("../x")` 允许逃出插件目录。
- 动态命令 API 允许传入别的 `plugin_id`。
- `run_system_action()` 允许执行任意 shell 字符串。
- 后台插件注入专属 API 后没有恢复 `ctx.platform`。
- `PlatformApi` 缓存了某个插件的 storage/commands 对象，导致多个插件串用同一命名空间。

## 后续路线

第一阶段完成后，再考虑：

1. `platform.window`：隐藏/显示 Launcher、退出当前插件、调整 inline view 高度。
2. `platform.input`：自动粘贴文本、模拟快捷键，但必须先设计权限状态和焦点恢复。
3. `platform.screen.capture()`：截图能力，需要 macOS 屏幕录制权限处理。
4. `platform.clipboard.write_image()`：统一图片路径、QImage 和 QML URL 的转换。
5. `platform.system.current_browser_url()`：只在可验证浏览器中支持，不作为核心通用能力。


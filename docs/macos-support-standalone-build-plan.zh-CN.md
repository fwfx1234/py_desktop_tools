# macOS 支持与独立应用构建设计

本文是给后续低级模型执行的实现文档。目标是让当前 PySide6 + QML 桌面工具箱支持 macOS，并能构建独立可运行应用包。本阶段暂不处理 macOS 签名、公证、自动更新和安装器，只要求本机可构建、可双击运行、核心功能可用。

## 目标

- Windows 现有能力保持可用。
- macOS 上 `uv run app` 可以启动，不因 Windows API import 失败而崩溃。
- macOS 上可以通过全局热键唤起 Launcher。默认热键使用 `Option+Space`，配置文案仍可显示为 `Alt+Space`。
- macOS 上应用启动器可以扫描并启动 `.app` 应用。
- 构建产物是独立 `.app`，双击后不依赖源码目录。
- 打包后的 QML、插件 manifest、图标、JS、内置插件 Python 模块都能被加载。
- 数据库和缓存写入用户数据目录，不能写入项目目录或 `.app` 内部。

## 非目标

- 不做 Developer ID 签名。
- 不做 notarization 公证。
- 不做 DMG、PKG、自动更新、开机自启。
- 不把所有平台差异一次性抽象到完美状态，只做当前功能需要的最小平台层。
- 不重写插件架构，不改插件 manifest 的现有基本格式。

## 当前阻塞

当前代码中有几处会阻止 macOS 启动：

- `src/app/commands/command_index_db.py` 顶层直接访问 `ctypes.windll.user32/shell32/gdi32`，macOS import 时会失败。
- `src/app/main.py` 直接导入 `src/app/hotkey/win_hotkey_manager.py`，启动流程绑定 Windows 热键实现。
- `src/app/commands/command_service.py` 写死 Windows 系统命令、`.lnk` 扫描和 `os.startfile`。
- `src/features/app_launcher/runtime.py` 只知道 Windows `.lnk` 应用。
- `src/app/paths.py` 默认把数据写到项目 `data/`，独立应用不应写安装目录。
- `PluginManager` 通过 manifest 所在目录动态加载 runtime 文件；PyInstaller 对这种动态 import 不稳定，需要明确收集内置插件模块。

## 总体方案

新增一个平台能力层，主流程和插件都只依赖稳定接口，不直接依赖 Windows/macOS 实现。

平台层分两类对象：

- `PlatformServices`：内核私有服务集合，给 `main.py`、`CommandService`、热键注册、应用索引用。
- `PlatformApi`：插件公开能力接口，放进 `PluginContext`，插件只能使用这个 API，不能直接拿到底层实现对象。

这个分层很重要：插件以后会越来越多，如果插件直接 import `apps_macos.py`、`hotkey_windows.py` 或直接调用 `subprocess/os.startfile`，平台兼容性会重新散落到各个插件里。

新增目录：

```text
src/app/platform/
  __init__.py
  api.py
  models.py
  factory.py
  services.py
  hotkey_base.py
  hotkey_windows.py
  hotkey_macos.py
  apps_base.py
  apps_windows.py
  apps_macos.py
  system_commands.py
  external_launcher.py
```

平台层负责：

- 创建内核使用的全局热键管理器。
- 扫描系统应用。
- 启动系统应用、文件、目录、URL 或系统命令。
- 提供平台名、默认热键、用户数据目录、缓存目录、资源目录。
- 向插件暴露受控的平台能力。

内核层负责：

- 插件发现和生命周期。
- Launcher 搜索与 QML 桥接。
- 窗口显示、隐藏、居中。
- 托盘或菜单栏入口。

插件层规则：

- 插件运行时通过 `ctx.platform` 获取平台能力。
- 插件不直接 import `app.platform.*_windows` 或 `app.platform.*_macos`。
- 插件不直接调用 `os.startfile`、`open -a`、`explorer.exe`、`ctypes.windll`。
- 插件需要系统能力时，优先调用 `PlatformApi`。

## 数据模型

`CommandIndexDb` 需要从 Windows `.lnk` 模型改成通用应用条目模型。

推荐表结构：

```sql
CREATE TABLE IF NOT EXISTS app_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    launch_path TEXT NOT NULL,
    bundle_id TEXT NOT NULL DEFAULT '',
    icon_path TEXT NOT NULL DEFAULT '',
    pinyin TEXT NOT NULL DEFAULT '',
    pinyin_initials TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    UNIQUE(platform, launch_path)
);
```

对外返回字段：

```python
{
    "id": row_id,
    "platform": platform,
    "name": name,
    "launchPath": launch_path,
    "bundleId": bundle_id,
    "iconPath": icon_path,
    "initials": pinyin_initials,
    "lnkPath": launch_path,  # 仅短期兼容旧调用
}
```

迁移规则：

- 如果旧表存在 `lnk_path` 且不存在 `launch_path`，新建通用表，把旧数据迁移为 `platform="windows"`、`launch_path=lnk_path`。
- 迁移完成后无需立刻删除旧表，可以重命名为 `app_entries_legacy` 或只保留新表。
- `record_launch_by_lnk()` 保留为兼容方法，内部转调 `record_launch(f"app:{path}")`。
- 新增 `record_launch_by_app_path(path)`。

## 平台接口设计

### 设计原则

- 平台能力以对象方法暴露，不让调用方拼命令行字符串。
- 方法失败时返回结构化结果，不把异常扩散到插件 UI。
- 插件公开 API 不暴露热键注册工厂。热键属于内核生命周期，插件 v1 只能通过 manifest 声明 hotkey。
- 所有路径返回字符串时使用本机路径格式；传给 QML 的图片路径再转成 `file:///`。
- 平台实现模块只在对应平台导入，避免 macOS import Windows API 失败。

### `models.py`

定义平台层通用数据结构：

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


PlatformName = Literal["windows", "macos", "unknown"]


@dataclass(frozen=True, slots=True)
class PlatformInfo:
    name: PlatformName
    display_name: str
    version: str = ""
    is_packaged: bool = False


@dataclass(frozen=True, slots=True)
class PlatformResult:
    ok: bool
    message: str = ""
    code: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AppEntry:
    platform: PlatformName
    name: str
    launch_path: str
    bundle_id: str = ""
    icon_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_db_dict(self) -> dict:
        return {
            "platform": self.platform,
            "name": self.name,
            "launch_path": self.launch_path,
            "bundle_id": self.bundle_id,
            "icon_path": self.icon_path,
        }


@dataclass(frozen=True, slots=True)
class SystemCommand:
    id: str
    name: str
    description: str
    icon: str
    action: str
    keywords: list[str]

    def to_item_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "action": self.action,
            "keywords": self.keywords,
        }
```

低级模型可以先用 dict 实现内部流转，但公开边界要按这些字段命名。

### `api.py`

`PlatformApi` 是插件可用的唯一平台能力入口。它应该是普通 Python 对象，不需要继承 `QObject`。如果未来 QML 也要直接调用，再另做 `QObject` 包装。

定义：

```python
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.platform.models import AppEntry, PlatformInfo, PlatformResult, SystemCommand

if TYPE_CHECKING:
    from app.platform.services import PlatformServices


class PlatformApi:
    def __init__(self, services: "PlatformServices") -> None:
        self._services = services

    @property
    def info(self) -> PlatformInfo:
        return self._services.info

    def is_windows(self) -> bool:
        return self.info.name == "windows"

    def is_macos(self) -> bool:
        return self.info.name == "macos"

    def user_data_dir(self) -> Path:
        return self._services.paths.user_data_dir()

    def cache_dir(self) -> Path:
        return self._services.paths.cache_dir()

    def resource_root(self) -> Path:
        return self._services.paths.resource_root()

    def scan_applications(self) -> list[AppEntry]:
        return self._services.app_indexer.scan_apps(self.cache_dir() / "app_icons")

    def system_commands(self) -> list[SystemCommand]:
        return self._services.system_commands.commands()

    def open_path(self, path: str | Path) -> PlatformResult:
        return self._services.external_launcher.open_path(path)

    def reveal_in_file_manager(self, path: str | Path) -> PlatformResult:
        return self._services.external_launcher.reveal_in_file_manager(path)

    def open_url(self, url: str) -> PlatformResult:
        return self._services.external_launcher.open_url(url)

    def launch_application(self, app: AppEntry | dict) -> PlatformResult:
        return self._services.external_launcher.launch_app(app)

    def run_system_action(self, action: str) -> PlatformResult:
        return self._services.external_launcher.launch_system_action(action)
```

插件使用示例：

```python
def on_enter(self, ctx: PluginContext, action: PluginAction):
    platform = ctx.platform
    if platform is None:
        raise RuntimeError("Platform API is unavailable")
    data_dir = platform.user_data_dir()
```

### `services.py`

`PlatformServices` 是内核私有对象，插件不要直接使用。

定义：

```python
from __future__ import annotations

from dataclasses import dataclass

from app.platform.api import PlatformApi
from app.platform.models import PlatformInfo


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

    def create_api(self) -> PlatformApi:
        return PlatformApi(self)
```

调用方需要平台名时使用：

```python
platform_services.info.name
platform_services.info.display_name
```

不要继续散落使用 `sys.platform` 判断，除了 `factory.py` 和少数底层实现模块。

### `paths` 能力

新增 `src/app/platform/paths.py` 或继续使用 `src/app/paths.py`，但要通过 `PlatformServices.paths` 暴露。

必须提供：

```python
class PlatformPaths:
    def project_root(self) -> Path:
        ...

    def resource_root(self) -> Path:
        ...

    def user_data_dir(self) -> Path:
        ...

    def cache_dir(self) -> Path:
        ...

    def db_path(self, name: str) -> Path:
        ...
```

现有 `app.paths.data_dir()`、`cache_dir()`、`db_path()` 可以作为兼容函数保留，但内部调用同一套路径实现。

### 插件上下文改造

修改 `src/app/plugins/runtime.py`：

```python
@dataclass(slots=True)
class PluginContext:
    command_index: object | None = None
    dynamic_commands: object | None = None
    platform: object | None = None
    services: dict[str, object] = field(default_factory=dict)
```

规则：

- 新插件优先使用 `ctx.platform`。
- `ctx.services["platform"]` 不再作为推荐入口，可以短期保留兼容。
- `ctx.services` 继续用于插件之间共享服务，例如 `clipboard.background`。

在 `main.py` 创建：

```python
platform_services = create_platform_services(qt_app)
platform_api = platform_services.create_api()

plugin_context = PluginContext(
    command_index=command_index,
    dynamic_commands=dynamic_commands,
    platform=platform_api,
    services={"platform": platform_api},
)
```

注意：`LauncherBridge` 当前拿的是 `plugin_context.services`，因此要继续保持同一个 dict 对象传入。

### 能力边界

本阶段 `PlatformApi` 暴露以下能力：

| 能力 | 方法 | Windows | macOS |
|---|---|---|---|
| 平台信息 | `info` | 支持 | 支持 |
| 用户数据目录 | `user_data_dir()` | `%APPDATA%/PyDesktopTools` | `~/Library/Application Support/PyDesktopTools` |
| 缓存目录 | `cache_dir()` | 用户数据目录下 `cache` | 用户数据目录下 `cache` |
| 资源根目录 | `resource_root()` | 源码根或 `_MEIPASS` | 源码根或 `_MEIPASS` |
| 扫描应用 | `scan_applications()` | `.lnk` | `.app` |
| 启动应用 | `launch_application()` | `os.startfile` | `open <app>` |
| 打开路径 | `open_path()` | `os.startfile` | `open <path>` |
| 文件管理器中显示 | `reveal_in_file_manager()` | `explorer /select,` | `open -R` |
| 打开 URL | `open_url()` | `QDesktopServices` 或 `start` | `QDesktopServices` 或 `open` |
| 系统命令列表 | `system_commands()` | 支持 | 支持 |
| 执行系统动作 | `run_system_action()` | 支持 | 支持 |

本阶段不向插件暴露以下能力：

- 注册任意全局热键。
- 监听全局键盘事件。
- 操作窗口置顶、穿透、虚拟桌面。
- macOS 辅助功能授权引导的 GUI 自动化。

插件如果需要热键，只能继续在 manifest 命令里声明 `hotkey`，由内核统一注册和管理。

### 错误处理约定

平台 API 方法不要让常见系统失败直接抛到插件层。推荐返回：

```python
PlatformResult(ok=False, code="not_found", message="路径不存在")
PlatformResult(ok=False, code="permission_denied", message="没有权限")
PlatformResult(ok=False, code="unsupported", message="当前平台不支持")
PlatformResult(ok=False, code="failed", message=str(exc))
```

允许抛异常的情况：

- 编程错误，例如参数类型完全错误。
- 初始化时必要组件缺失且无法降级。

插件调用后应按 `result.ok` 判断，不要解析 message。

### `hotkey_base.py`

定义协议：

```python
from typing import Protocol

class HotkeyManagerProtocol(Protocol):
    hotkeyPressed: object

    def register(self, hotkey: str | None = None) -> bool:
        ...

    def unregister(self) -> None:
        ...

    def is_registered(self) -> bool:
        ...
```

工厂协议：

```python
class HotkeyFactoryProtocol(Protocol):
    def create(self, *, parent: object | None, hotkey: str, hotkey_id: int) -> HotkeyManagerProtocol:
        ...

    def install_filter(self, app: object, manager: HotkeyManagerProtocol) -> object | None:
        ...
```

Windows 需要 native event filter，macOS 不需要，所以 `install_filter()` 可以返回 `None`。

### `factory.py`

按 `sys.platform` 返回平台服务：

- `win32`：Windows 实现。
- `darwin`：macOS 实现。
- 其他平台：返回 no-op 热键、空应用索引、基础系统命令。其他平台不是本阶段目标，但不能 import 崩溃。

### no-op 实现

新增：

```text
src/app/platform/hotkey_noop.py
src/app/platform/apps_noop.py
src/app/platform/external_noop.py
```

要求：

- `NoopHotkeyManager.register()` 返回 `False`。
- `NoopAppIndexer.scan_apps()` 返回空列表。
- `NoopExternalLauncher` 所有方法返回 `PlatformResult(ok=False, code="unsupported")`。
- unknown 平台仍可以启动应用主界面，只是没有全局热键和系统应用启动器。

no-op 实现是防回归保险：低级模型不能在非目标平台 import 时崩溃。

## 热键实现

### Windows

把现有 `src/app/hotkey/win_hotkey_manager.py` 迁移或包装到：

```text
src/app/platform/hotkey_windows.py
```

要求：

- 顶层可以继续使用 `ctypes.windll`，但此模块只能在 Windows 分支导入。
- 保持 `WinHotkeyManager` 和 `WinHotkeyFilter` 行为不变。
- `WindowsHotkeyFactory.install_filter()` 创建并安装 `WinHotkeyFilter`，返回 filter 对象，调用方需要持有引用。

### macOS

新增：

```text
src/app/platform/hotkey_macos.py
```

本阶段建议用 `pynput`，因为实现成本低，适合先跑通：

- 依赖：`pynput; sys_platform == "darwin"`。
- 使用 `pynput.keyboard.Listener` 监听按键。
- 解析 `Alt`、`Option` 为同一修饰键。
- 支持至少这些按键：
  - `Alt+Space`
  - `Option+Space`
  - `Alt+V`
  - `Option+V`
  - `Ctrl+Alt+V`
  - `Cmd+Space` 允许解析但不建议默认使用，因为会和 Spotlight 冲突。
- 回调线程里不能直接操作 QML。只允许发 Qt signal；如果发现跨线程不稳定，使用 `QTimer.singleShot(0, self.hotkeyPressed.emit)`。
- 注册失败返回 `False`，应用继续启动。
- 如果权限不足或 `pynput` import 失败，打印警告，不抛异常。

默认热键：

- Launcher：`Alt+Space`，macOS 实际按键是 `Option+Space`。
- 剪贴板：`Alt+V`，macOS 实际按键是 `Option+V`。

低级模型不要把默认热键改成 `Cmd+Space`。

## 应用扫描与启动

### 通用接口

`apps_base.py` 定义内核私有扫描接口：

```python
from typing import Protocol
from pathlib import Path

class AppIndexerProtocol(Protocol):
    def scan_apps(self, icon_dir: Path | None = None) -> list[AppEntry]:
        ...
```

返回 `AppEntry`，字段统一为：

```python
AppEntry(
    platform="macos",
    name="Visual Studio Code",
    launch_path="/Applications/Visual Studio Code.app",
    bundle_id="com.microsoft.VSCode",
    icon_path="/.../cache/app_icons/xxxx.png",
)
```

Windows 返回 `platform="windows"`，`launch_path` 是 `.lnk` 路径。

### Windows

把 `scan_windows_shortcuts()` 和图标提取逻辑移动到：

```text
src/app/platform/apps_windows.py
```

要求：

- `src/app/commands/command_index_db.py` 不再 import `ctypes`。
- Windows 图标提取逻辑仍只在 Windows 模块中存在。
- 原来的 `lnk_path` 字段改为 `launch_path`，同时为了兼容可以返回 `lnk_path`。

### macOS

新增：

```text
src/app/platform/apps_macos.py
```

扫描目录：

```text
/Applications
~/Applications
/System/Applications
/Applications/Utilities
```

扫描规则：

- 只扫描后缀 `.app` 的目录。
- 读取 `Contents/Info.plist`。
- 名称优先级：
  1. `CFBundleDisplayName`
  2. `CFBundleName`
  3. `.app` 目录名去掉后缀
- `bundle_id` 使用 `CFBundleIdentifier`，没有则为空字符串。
- 跳过不存在、无权限、Info.plist 解析失败的应用，不抛异常。
- 同路径去重；同名不同路径允许保留。

图标：

- v1 可以先不提取图标，使用默认 `qta:mdi6.application-outline`。
- 如果实现图标，优先用 Qt 的 `QFileIconProvider` 对 `.app` 目录取 icon，然后保存 PNG 到 `icon_dir`。
- 不要直接把 `.icns` 路径传给 QML，兼容性不够稳定。

启动：

`external_launcher.py` 提供内核私有启动实现，`PlatformApi` 会包装这些方法：

```python
class ExternalLauncher:
    def launch_app(self, app: AppEntry | dict) -> PlatformResult:
        ...

    def launch_system_action(self, action: str) -> PlatformResult:
        ...

    def open_path(self, path: str | Path) -> PlatformResult:
        ...

    def reveal_in_file_manager(self, path: str | Path) -> PlatformResult:
        ...

    def open_url(self, url: str) -> PlatformResult:
        ...
```

macOS 启动应用：

```python
subprocess.Popen(["open", launch_path])
```

Windows 启动应用：

```python
os.startfile(launch_path)
```

## 系统命令

把 `CommandService.SYSTEM_COMMANDS` 改为平台提供。

新增 `system_commands.py`：

```python
class SystemCommandProvider:
    def commands(self) -> list[SystemCommand]:
        ...
```

Windows 保留当前命令：

- 此电脑：`explorer.exe`
- 控制面板：`control.exe`
- 命令提示符：`cmd.exe`
- 任务管理器：`taskmgr.exe`
- 记事本：`notepad.exe`
- 计算器：`calc.exe`
- 重启应用：`__restart_app__`

macOS 命令：

- Finder：`open -a Finder`
- 系统设置：`open -a "System Settings"`
- 终端：`open -a Terminal`
- 活动监视器：`open -a "Activity Monitor"`
- 计算器：`open -a Calculator`
- 重启应用：`__restart_app__`

命令对象通过 `SystemCommand.to_item_dict()` 转为现有字段：

```python
SystemCommand(
    id="terminal",
    name="终端",
    icon="qta:mdi6.console",
    description="打开终端",
    action="open -a Terminal",
    keywords=["terminal", "shell", "终端"],
)
```

`CommandService.launch_external_item()` 不要自己 `subprocess.Popen(..., shell=True)`。改为调用平台 `external_launcher`。

## 主入口改造

修改 `src/app/main.py`：

1. 删除直接导入：

```python
from .hotkey.win_hotkey_manager import WinHotkeyManager, WinHotkeyFilter
```

2. 新增：

```python
from .platform.factory import create_platform_services
```

3. 创建 QApplication 后：

```python
platform_services = create_platform_services(qt_app)
```

4. 创建 `PlatformApi`，并注入插件上下文：

```python
platform_api = platform_services.create_api()
```

5. 创建 `CommandService` 时传入平台服务：

```python
command_service = CommandService(
    manifests,
    command_index,
    dynamic_commands,
    platform_services=platform_services,
)
```

6. 创建 `PluginContext` 时传入平台 API：

```python
plugin_context = PluginContext(
    command_index=command_index,
    dynamic_commands=dynamic_commands,
    platform=platform_api,
    services={"platform": platform_api},
)
```

`services["platform"]` 是兼容入口；新代码应使用 `ctx.platform`。

7. 热键创建改为：

```python
hotkey_mgr = platform_services.hotkey_factory.create(
    parent=qt_app,
    hotkey=platform_services.default_launcher_hotkey,
    hotkey_id=1,
)
clipboard_hotkey_mgr = platform_services.hotkey_factory.create(
    parent=qt_app,
    hotkey=platform_services.default_clipboard_hotkey,
    hotkey_id=2,
)
```

8. Windows 的 `set_hwnd()` 只在对象有该方法时调用：

```python
set_hwnd = getattr(manager, "set_hwnd", None)
if callable(set_hwnd):
    set_hwnd(hwnd)
```

9. native event filter 安装改为工厂处理：

```python
hotkey_filter = platform_services.hotkey_factory.install_filter(qt_app, hotkey_mgr)
if hotkey_filter is not None:
    hotkey_filters.append(hotkey_filter)
```

10. `qt_app.setProperty("_hotkeyFilters", hotkey_filters)` 保存 filter 引用，避免被 GC。

11. 插件热键也使用平台工厂，不再写死 `WinHotkeyManager`。

12. shutdown 时仍统一调用所有 manager 的 `unregister()`。

## CommandService 改造

修改 `src/app/commands/command_service.py`：

- 删除 `scan_windows_shortcuts`、`os.startfile` 的 import。
- 构造函数新增 `platform_services`。
- `_apps_scanned` 保持。
- 搜索首次扫描时调用：

```python
self._index_db.sync_apps(
    [app.to_db_dict() for app in self._platform.app_indexer.scan_apps(self._index_db.get_icon_dir())]
)
```

- `_system_items()` 使用：

```python
for index, command in enumerate(self._platform.system_commands.commands()):
    item = command.to_item_dict()
    ...
```

- `launch_external_item()`：
  - `source == "system"` 且 action 是 `__restart_app__`，仍由 `LauncherBridge` 处理。
  - 其他 system 调用 `self._platform.external_launcher.launch_system_action(action)`。
  - app 调用 `self._platform.external_launcher.launch_app(payload)`。
  - 如果返回 `PlatformResult.ok` 为 `False`，打印 warning，并返回 `None`。

- `_app_items()` 从 `app["launchPath"]` 读取路径。

## App Launcher 插件改造

修改 `src/features/app_launcher/runtime.py`：

- 文案从 “Windows 应用程序” 改成 “系统应用程序”。
- 不再 import `scan_windows_shortcuts`。
- 从 `ctx.platform` 里取平台 API，兼容回退到 `ctx.services["platform"]`：

```python
platform = ctx.platform or ctx.services.get("platform")
if platform is None:
    raise RuntimeError("Platform API is unavailable")
```

- `_rescan()` 调用：

```python
apps = self._platform.scan_applications()
self._command_index.sync_apps([app.to_db_dict() for app in apps])
```

- `on_list_item_selected()` 调用平台 API：

```python
result = self._platform.launch_application(app)
if not result.ok:
    print(f"[WARN] 启动应用失败: {result.code} {result.message}")
```

同时在 `main.py` 创建 `PluginContext` 时注入：

```python
platform_api = platform_services.create_api()
plugin_context = PluginContext(
    command_index=command_index,
    dynamic_commands=dynamic_commands,
    platform=platform_api,
    services={"platform": platform_api},
)
```

注意：当前代码先创建 `PluginContext` 后 `BackgroundManager`，低级模型要保持已有 `services` dict 被传给 `LauncherBridge`。

## 插件使用平台能力规范

所有插件都可以通过 `PluginContext.platform` 使用平台能力。

### 推荐写法

```python
class SomeRuntime:
    def on_enter(self, ctx: PluginContext, action: PluginAction):
        platform = ctx.platform
        if platform is None:
            raise RuntimeError("Platform API is unavailable")
        cache_dir = platform.cache_dir()
        return SomeSession(platform)
```

ViewModel 如果需要平台能力，由 Runtime 构造时传入：

```python
view_model = SomeViewModel(platform=ctx.platform)
```

不要在 ViewModel 里重新 import 平台实现模块。

### 常用场景

打开文件或目录：

```python
result = platform.open_path(path)
if not result.ok:
    self.errorChanged.emit(result.message)
```

在文件管理器中定位文件：

```python
platform.reveal_in_file_manager(path)
```

打开网页：

```python
platform.open_url("https://example.com")
```

扫描系统应用：

```python
apps = platform.scan_applications()
```

判断平台：

```python
if platform.is_macos():
    ...
```

### 禁止写法

插件中不要出现：

```python
os.startfile(...)
subprocess.Popen(["open", ...])
ctypes.windll
from app.platform.apps_macos import ...
from app.platform.hotkey_windows import ...
sys.platform == "darwin"
```

例外：如果插件实现的是明确的平台专属功能，并且 manifest 或 runtime 已经声明只在某个平台可用，才允许在插件内部做平台判断。本阶段不新增这类平台专属插件。

### 能力不足时的处理

如果插件需要的新平台能力不在 `PlatformApi` 中，不要绕过平台层。应先扩展：

1. `models.py` 中的数据结构。
2. `api.py` 的公开方法。
3. `services.py` 的内部依赖。
4. Windows/macOS/no-op 三套实现。
5. 本文档的能力边界和验收步骤。

这样后续插件不会把平台差异重新扩散出去。

## 路径与打包资源

修改 `src/app/paths.py`。

新增函数：

```python
def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))

def resource_root() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]

def user_data_dir() -> Path:
    configured = os.getenv("PY_DESKTOP_TOOLS_DATA_DIR", "").strip()
    if configured:
        root = Path(configured)
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support" / "PyDesktopTools"
    elif os.name == "nt":
        root = Path(os.getenv("APPDATA", str(Path.home()))) / "PyDesktopTools"
    else:
        root = Path.home() / ".local" / "share" / "py-desktop-tools"
    root.mkdir(parents=True, exist_ok=True)
    return root
```

调整：

- `data_dir()` 返回 `user_data_dir()`。
- `cache_dir()` 基于 `data_dir()`。
- `project_root()` 仅用于源码开发场景，不能被数据库和缓存默认使用。

修改 `manifest_loader.py`：

- 内置插件目录不能固定依赖 `Path(__file__).parents[2] / "features"`。
- 使用 `resource_root()`。
- 兼容源码和 PyInstaller：

```python
def default_bundled_plugin_dirs() -> list[Path]:
    root = resource_root()
    candidates = [
        root / "src" / "features",
        root / "features",
    ]
    return [path for path in candidates if path.is_dir()]
```

外部插件目录仍使用环境变量或用户插件目录。

## 打包方案

本阶段使用 PyInstaller。

新增构建依赖：

```toml
[dependency-groups]
build = [
    "pyinstaller>=6.0",
]
```

新增平台依赖：

```toml
"pynput>=1.7.7; sys_platform == 'darwin'"
```

`pylnk3` 当前未实际使用。如果保留，建议加平台 marker：

```toml
"pylnk3>=0.4.2; sys_platform == 'win32'"
```

新增：

```text
build/pyinstaller/py_desktop_tools.spec
tools/build_macos.sh
tools/build_windows.ps1
```

spec 要点：

- app 名称：`PyDesktopTools`
- 入口：`src/app/main.py`
- macOS 使用 `windowed=True`
- 收集 PySide6、qtawesome、Pillow、qrcode、requests、websocket-client、opencv-python 所需模块。
- 显式收集：
  - `src/app/**/*.qml`
  - `src/app/**/*.js`
  - `src/app/assets/**`
  - `src/app/theme/**`
  - `src/app/ui/**`
  - `src/features/**/*.qml`
  - `src/features/**/*.js`
  - `src/features/**/*.json`
  - `src/features/**/*.svg`
- hidden imports 至少包含：
  - `app`
  - `app.main`
  - `app.platform.factory`
  - `app.platform.hotkey_windows`
  - `app.platform.hotkey_macos`
  - 所有 `features.*.runtime`
  - 所有 `features.*.view_model`
  - 所有 `features.*.service`

低级模型可用 PyInstaller hook 工具：

```python
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
```

建议 hiddenimports：

```python
hiddenimports = (
    collect_submodules("app")
    + collect_submodules("features")
)
```

建议 datas：

```python
datas = [
    ("src/app", "src/app"),
    ("src/features", "src/features"),
]
```

如果 datas 过大，后续再精简；v1 优先保证可运行。

macOS 构建脚本：

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --group build
uv run pyinstaller build/pyinstaller/py_desktop_tools.spec --noconfirm
```

Windows 构建脚本：

```powershell
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
uv sync --group build
uv run pyinstaller build\pyinstaller\py_desktop_tools.spec --noconfirm
```

## 实施顺序

按以下顺序执行，不要跳步：

1. 新增 `src/app/platform/models.py`、`api.py`、`services.py`，先定义 `PlatformApi`、`PlatformServices`、`PlatformResult`、`AppEntry`、`SystemCommand`。
2. 新增 no-op 平台实现和 `factory.py`，确保 unknown 平台可启动但能力返回 unsupported。
3. 修改 `PluginContext`，增加 `platform` 字段，并在 `main.py` 注入 `platform_api`。
4. 移动 Windows 热键到平台层，`main.py` 通过 `platform_services.hotkey_factory` 创建热键。
5. 移动 Windows 应用扫描到平台层，确保 `command_index_db.py` 在 macOS 不会 import Windows API。
6. 改造 `CommandIndexDb` 的 `app_entries` 通用 schema 和兼容迁移。
7. 改造 `CommandService`，让系统命令、应用扫描、应用启动都通过 `PlatformServices`。
8. 改造 `app_launcher` 插件，让它通过 `ctx.platform` 扫描和启动应用。
9. 新增 macOS 应用扫描。
10. 新增 macOS 热键。
11. 改造 `paths.py` 和 `manifest_loader.py`，支持源码路径和打包资源路径，并让 `PlatformApi` 暴露路径能力。
12. 增加 PyInstaller spec 和构建脚本。
13. 更新 README 或新增简短运行说明，注明 macOS 需要辅助功能权限才能使用全局热键。
14. 做 Windows 回归。
15. 做 macOS 源码运行验证。
16. 做 macOS `.app` 构建验证。

## 验收步骤

### Windows

```powershell
uv sync
uv run app
```

验证：

- 应用启动。
- `Alt+Space` 打开 Launcher。
- 搜索插件正常。
- 应用启动器能扫描并启动 Windows 应用。
- 剪贴板历史热键 `Alt+V` 正常。
- 关闭应用时无异常。

构建：

```powershell
tools\build_windows.ps1
```

验证：

- 构建产物能启动。
- 插件 QML 能加载。
- 应用数据写入用户数据目录。

### macOS

```bash
uv sync
uv run app
```

验证：

- 应用启动。
- 没有 `ctypes.windll`、`os.startfile`、`WinHotkeyManager` 相关 import 错误。
- 授予辅助功能权限后，`Option+Space` 能打开 Launcher。
- 如果未授权，应用仍可启动，并打印热键注册失败警告。
- 应用启动器能列出 `/Applications` 下的 `.app`。
- 点击应用条目可以启动对应应用。
- API 测试、JSON、QR、图片压缩、剪贴板插件能打开。

构建：

```bash
tools/build_macos.sh
open dist/PyDesktopTools.app
```

验证：

- `.app` 双击或 `open` 可启动。
- 不依赖源码目录。
- QML 页面和内置插件正常加载。
- 数据库生成在 `~/Library/Application Support/PyDesktopTools`。

## 常见失败处理

- 如果 macOS 启动时报 `ctypes.windll`：说明仍有 Windows 模块在非 Windows 平台被 import，继续把该 import 移入 Windows 分支。
- 如果 macOS 热键无效但应用能启动：先检查辅助功能权限；本阶段接受未授权时热键失败。
- 如果打包后插件打不开：检查 PyInstaller hiddenimports 是否包含 `features.*`，datas 是否包含 `src/features`。
- 如果打包后 QML 找不到：检查 datas 是否包含 `src/app` 和 `src/features`，以及 `resource_root()` 是否返回了 `_MEIPASS`。
- 如果应用启动器为空：检查 `apps_macos.py` 是否扫描 `.app` 目录，检查 `CommandIndexDb.sync_apps()` 是否使用 `launch_path`。
- 如果 Windows 应用启动器坏了：检查旧字段 `lnkPath` 是否仍兼容，`os.startfile` 是否只在 Windows external launcher 中调用。

## 完成定义

低级模型完成后，应满足：

- Windows 和 macOS 都能源码运行。
- macOS 上没有 Windows API 导入错误。
- 平台差异集中在 `src/app/platform/`。
- 插件通过 `ctx.platform` 使用平台能力，不直接 import 平台具体实现。
- `PlatformApi` 至少提供平台信息、路径、应用扫描、应用启动、打开路径、文件管理器定位、打开 URL、系统命令能力。
- 平台 API 常见失败返回 `PlatformResult`，不把普通系统失败抛到插件层。
- `CommandService`、`app_launcher` 不再直接调用 Windows API。
- 数据目录适合独立应用。
- PyInstaller 可以生成可运行的 `.app`。
- 文档中“非目标”没有被擅自扩展实现。

# Py Desktop Tools 插件开发文档（完整版）

本文档是 py-desktop-tools 插件系统的权威参考。面向自带插件和第三方插件开发者。

---

## 目录

1. [核心原则](#1-核心原则)
2. [快速上手：5 分钟创建插件](#2-快速上手5-分钟创建插件)
3. [项目结构规范](#3-项目结构规范)
4. [plugin.json 完整字段参考](#4-pluginjson-完整字段参考)
5. [命令声明与搜索优化](#5-命令声明与搜索优化)
6. [Runtime：插件生命周期](#6-runtime插件生命周期)
7. [Session：插件会话管理](#7-session插件会话管理)
8. [ViewModel：MVVM 架构中的业务桥](#8-viewmodelmvvm-架构中的业务桥)
9. [Service：纯 Python 业务层](#9-service纯-python-业务层)
10. [QML 页面开发](#10-qml-页面开发)
11. [launchMode 详解](#11-launchmode-详解)
12. [background 后台插件](#12-background-后台插件)
13. [上下文推荐 Matchers](#13-上下文推荐-matchers)
14. [前缀系统](#14-前缀系统)
15. [动态命令](#15-动态命令)
16. [插件间通信](#16-插件间通信)
17. [资源清理](#17-资源清理)
18. [插件验收清单](#18-插件验收清单)
19. [故障排查](#19-故障排查)
20. [附录：内置插件速查](#20-附录内置插件速查)

---

## 1. 核心原则

> 插件自己声明"我是谁、我提供什么命令、我适合什么输入"；核心应用只负责发现插件、统一排序、按需加载和提供受控 API。

**框架不感知插件业务逻辑**。`CommandService` 里没有 `if plugin_id == "xxx"` 这种判断。所有差异化能力都通过 Manifest 声明。

**懒加载**。读取 `plugin.json` 时不 import 任何插件 Python 代码。Runtime 只在用户启动插件或后台启动时才加载。

**MVVM 分层**。QML = View，Python QObject = ViewModel，纯 Python 类 = Service。不要把所有逻辑写进 QML 的 `function()` 块里。

---

## 2. 快速上手：5 分钟创建插件

### 2.1 最小文件集

```
src/features/my_tool/
├── plugin.json
├── runtime.py
├── view_model.py
└── MyToolPage.qml
```

### 2.2 plugin.json

```json
{
  "id": "my-tool",
  "name": "我的工具",
  "version": "0.1.0",
  "description": "一个示例工具",
  "icon": "qta:mdi6.tools",
  "entrypoint": "runtime:create_runtime",
  "qmlPage": "MyToolPage.qml",
  "contextProperty": "myToolVm",
  "category": "tool",
  "order": 99,
  "commands": [
    {
      "id": "my-tool.open",
      "title": "我的工具",
      "subtitle": "示例工具描述",
      "icon": "qta:mdi6.tools",
      "keywords": ["我的", "工具", "示例"],
      "launchMode": "inline_view"
    }
  ]
}
```

### 2.3 runtime.py

```python
from app.plugins.runtime import SimpleQmlRuntime
from .view_model import MyToolViewModel

def create_runtime():
    return SimpleQmlRuntime(lambda _ctx: MyToolViewModel())
```

### 2.4 view_model.py

```python
from PySide6.QtCore import QObject, Signal, Slot

class MyToolViewModel(QObject):
    resultReady = Signal(str)

    @Slot(str)
    def process(self, text: str) -> None:
        self.resultReady.emit(f"处理结果: {text.upper()}")

    def dispose(self):
        """清理资源：停止任务、Timer 或关闭 Service。"""
        pass
```

### 2.5 MyToolPage.qml

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../app/ui"
import "../../app/theme"

Item {
    id: root
    readonly property bool dark: app.theme === "dark"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        UiTextField {
            id: input
            dark: root.dark
            Layout.fillWidth: true
            placeholderText: "输入文本"
        }

        UiButton {
            text: "处理"
            dark: root.dark
            variant: "primary"
            onClicked: myToolVm.process(input.text)
        }

        UiTextArea {
            id: output
            dark: root.dark
            readOnly: true
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }

    Connections {
        target: myToolVm
        function onResultReady(text) { output.text = text }
    }
}
```

### 2.6 验收三步

```powershell
# 1. 检查清单是否正确加载
uv run python -c "
import sys; sys.path.insert(0, 'src')
from app.plugins.manifest_loader import load_all_plugin_manifests
for m in load_all_plugin_manifests():
    print(f'{m.id}: {m.name}')
"

# 2. 启动应用实测
uv run app
```

按 `Alt+Space`，搜索"我的工具"即可看到新插件。

---

## 3. 项目结构规范

### 3.1 自带插件（bundled）

```
src/features/<plugin-name>/
├── plugin.json              # 必须：插件清单
├── runtime.py               # 必须：Runtime 工厂
├── view_model.py            # 推荐：ViewModel
├── service.py               # 可选：纯业务 Service
├── <Page>.qml               # 推荐：主页面
├── components/              # 可选：该插件的 QML 子组件
│   ├── SubComponent.qml
│   └── ...
├── assets/                  # 可选：图标、图片等资源
│   └── icon.svg
└── __init__.py              # 可空文件，使目录成为 Python 包
```

### 3.2 外部插件（external）

```text
plugins/
└── my-plugin/
    ├── plugin.json
    ├── runtime.py
    ├── view_model.py
    ├── pages/
    │   └── MainPage.qml
    └── README.md
```

通过环境变量指定外部插件目录：

```powershell
$env:PY_DESKTOP_TOOLS_PLUGIN_DIR = "D:\my_plugins;E:\team_plugins"
```

多个目录用 `;`（Windows）或 `:`（Linux/macOS）分隔。

### 3.3 多 Manifest 插件包

一个目录可以包含多个 Manifest 文件，共享同一份 Runtime 代码：

```text
src/features/system/
├── system-settings.plugin.json   # plugin.json 的变体
├── about.plugin.json
├── runtime.py                    # 共享 Runtime
├── SystemSettingsPage.qml
└── AboutPage.qml
```

框架会扫描 `plugin.json` 和 `*.plugin.json` 两种模式。

---

## 4. plugin.json 完整字段参考

```json
{
  "id": "my-tool",
  "name": "我的工具",
  "version": "1.0.0",
  "description": "工具描述",
  "icon": "qta:mdi6.tools",
  "entrypoint": "runtime:create_runtime",
  "qmlPage": "MyPage.qml",
  "contextProperty": "myToolVm",
  "activation": "lazy",
  "category": "tool",
  "order": 99,
  "window": { "width": 1000, "height": 600 },
  "commands": [ ... ]
}
```

### 核心字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `id` | string | **是** | 全局唯一标识，使用 `kebab-case`，如 `api-test` |
| `name` | string | **是** | 显示名称 |
| `entrypoint` | string | **是** | Runtime 工厂，格式 `模块名:函数名`，如 `runtime:create_runtime` |
| `version` | string | 否 | 语义化版本号 |
| `description` | string | 否 | 功能描述 |
| `icon` | string | 否 | 图标，支持格式见 4.1 |
| `qmlPage` | string | 否 | 插件 QML 页面路径，相对于插件目录 |
| `contextProperty` | string | 否 | ViewModel 注入到 QML 上下文的名字 |
| `activation` | string | 否 | `"lazy"`（默认）或 `"background"` |
| `category` | string | 否 | 分类标签 |
| `order` | int | 否 | 默认排序权重，越小越靠前 |
| `window` | object | 否 | 窗口模式配置，见 4.2 |
| `commands` | array | **是** | 命令列表，见第 5 章 |

### 4.1 icon 格式

| 格式 | 示例 | 说明 |
|------|------|------|
| qtawesome | `"qta:mdi6.api"` | Material Design 图标 |
| qtawesome | `"qta:fa5s.star"` | Font Awesome 图标 |
| 文件 URL | `"file:///D:/icons/tool.svg"` | 绝对路径 |
| 内置图标名 | `"json"` | 查找 `src/app/assets/icons/json.svg` |

### 4.2 window 配置

```json
"window": {
  "width": 0.8,
  "height": 0.8,
  "fullscreen": false
}
```

| 字段 | 说明 |
|------|------|
| `width` / `height` | `< 1.0` 表示屏幕比例，`>= 1` 表示绝对像素 |
| `fullscreen` | `true` 时全屏，覆盖 width/height |

默认窗口大小 800 x 600。当前插件 Session 仍按 `pluginId` 管理，因此同一个插件暂时只支持单窗口实例；如果后续要支持多实例，需要先引入 `sessionId`。

---

## 5. 命令声明与搜索优化

### 5.1 Command 完整字段

```json
{
  "id": "my-tool.open",
  "title": "我的工具",
  "subtitle": "功能简述",
  "icon": "qta:mdi6.tools",
  "keywords": ["关键词1", "关键词2"],
  "prefixes": ["my", "tool"],
  "launchMode": "inline_view",
  "inputMode": "plugin",
  "hotkey": "",
  "payload": {},
  "matchers": [
    { "source": "input", "kind": "json", "boost": 180 },
    { "source": "clipboard", "kind": "url", "boost": 80 }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `id` | 命令唯一 ID，建议 `插件id.动作` |
| `title` | 在搜索结果中显示的名称 |
| `subtitle` | 副标题/描述 |
| `keywords` | 搜索关键词，支持中文、英文、拼音自动匹配 |
| `prefixes` | 前缀词，如 `json`、`qr`，用于命令词激活 |
| `launchMode` | 见第 11 章 |
| `inputMode` | `"plugin"`（默认）或 `"global"`，控制输入传递方式 |
| `hotkey` | 全局快捷键，如 `"Ctrl+Shift+A"` |
| `payload` | 传递给 `PluginAction.payload` 的附加数据 |
| `matchers` | 上下文推荐规则，见第 13 章 |

### 5.2 搜索排序原理

搜索结果按以下优先级排序：

```
前缀精确命中 (score +240)
  > 标题/关键词匹配 (score 100-70)
  > 上下文 matcher 推荐 (boost 各插件声明)
  > 使用频率 (useCount)
  > 默认 order
```

### 5.3 调试搜索结果

```python
# 在 Python 中检查搜索结果及其推荐原因
result = {
    "name": "我的工具",
    "score": 230,
    "recommendReasons": ["prefix:my", "input:json"]  # 调试用
}
```

---

## 6. Runtime：插件生命周期

### 6.1 加载时机

```
应用启动
  → 扫描所有 plugin.json → PluginManifest 列表（轻量，不 import 插件代码）
  → 用户启动插件 OR 后台插件自动启动
  → PluginManager._load_runtime(manifest)
  → 解析 entrypoint → import 插件模块 → 调用工厂函数 → 得到 Runtime
```

非后台插件在应用启动时**不会**创建 ViewModel、不会加载 QML、不会 import 插件模块。

### 6.2 SimpleQmlRuntime（推荐）

大多数插件使用框架提供的 `SimpleQmlRuntime`：

```python
from app.plugins.runtime import SimpleQmlRuntime
from .view_model import MyViewModel

def create_runtime():
    return SimpleQmlRuntime(lambda _ctx: MyViewModel())
```

它为你做了：
- `on_enter()` → 创建 ViewModel → 返回 `QmlPluginSession`
- `on_exit()` → 空操作（资源清理由 Session.close() 处理）

### 6.3 自定义 Runtime

需要更复杂逻辑时自己实现：

```python
class MyCustomRuntime:
    def on_enter(self, ctx: PluginContext, action: PluginAction) -> PluginSession:
        # 读取 action.input_text, action.command_id, action.payload
        # 可使用 ctx.services, ctx.dynamic_commands
        view_model = MyViewModel(action.input_text)
        return QmlPluginSession(
            manifest=action.manifest,
            launch_mode=action.manifest.primary_command.launch_mode,
            view_model=view_model,
        )

    def on_exit(self) -> None:
        # 所有资源清理应在 Session.close() 中完成
        pass


def create_runtime():
    return MyCustomRuntime()
```

### 6.4 PluginContext —— 稳定的 API 边界

```python
@dataclass
class PluginContext:
    command_index: object | None        # CommandIndexDb 实例
    dynamic_commands: object | None     # DynamicCommandRegistry 实例
    platform: object | None             # PlatformApi，插件首选入口
    services: dict[str, object]         # 共享服务注册表
```

| 属性 | 用途 |
|------|------|
| `ctx.platform` | 平台能力入口，优先使用 |
| `ctx.services["clipboard.background"]` | 获取剪切板后台服务（监听、存储、读取） |
| `ctx.dynamic_commands` | 动态命令兼容入口，建议迁移到 `ctx.platform.commands` |
| `ctx.command_index` | 读取/写入启动次数和最近使用记录 |

推荐写法：

```python
def on_enter(self, ctx: PluginContext, action: PluginAction):
    platform = ctx.platform
    if platform is None:
        raise RuntimeError("Platform API is unavailable")

    settings = platform.storage.dict_store("settings", defaults={"enabled": True})
    text = platform.clipboard.read_text()
    screen = platform.screen.display_at_cursor()
```

优先使用这些能力：

- `ctx.platform.clipboard.read_text()` / `write_text()`
- `ctx.platform.dialogs.open_file()` / `open_directory()`
- `ctx.platform.storage.dict_store()` / `database()`
- `ctx.platform.commands.register()` / `unregister_all()`
- `ctx.platform.open_path()` / `open_url()`

### 6.5 PluginAction —— 启动参数

```python
@dataclass
class PluginAction:
    manifest: PluginManifest     # 当前 Manifest
    command_id: str              # 触发的命令 ID
    input_text: str              # 用户输入文本（去掉前缀后的业务内容）
    payload: dict                # Manifest 中声明的 payload
```

---

## 7. Session：插件会话管理

### 7.1 什么是 Session

用户每启动一次插件 = 创建一个 Session。Session 的生命周期：

```
打开插件 → Session 创建 → ViewModel 注入 QML → UI 加载
用户操作 → ViewModel 处理 → Signal 通知 QML
关闭插件 → Session.close() → ViewModel 清理 → QML context 设为 null → Runtime 引用移除
```

### 7.2 QmlPluginSession（框架提供）

```python
class QmlPluginSession:
    def __init__(self, manifest, launch_mode, view_model=None):
        self.manifest = manifest
        self.launch_mode = launch_mode
        self._view_model = view_model

    def create_qml_context(self) -> dict[str, QObject]:
        """返回要注入 QML 的 {contextProperty: viewModel} 字典"""
        if self._view_model and self.manifest.context_property:
            return {self.manifest.context_property: self._view_model}
        return {}

    def qml_page(self) -> str:
        """返回插件 QML 页面的 file:// URL"""
        return self.manifest.qml_page

    def close(self) -> None:
        """清理 ViewModel，先调 dispose() 再 deleteLater()"""
        if self._view_model:
            dispose = getattr(self._view_model, "dispose", None)
            if callable(dispose):
                try: dispose()
                except Exception as e: print(f"[WARN] dispose 失败: {e}")
            self._view_model.deleteLater()
            self._view_model = None
```

### 7.3 自定义 Session

如果需要 `list` 模式或 `on_input_changed` 功能：

```python
class MyListSession(QmlPluginSession):
    def list_model(self) -> list[dict]:
        return [{"id": "1", "title": "选项1"}, {"id": "2", "title": "选项2"}]

    def on_input_changed(self, text: str) -> list[dict]:
        return [item for item in self.list_model() if text in item["title"]]

    def on_list_item_selected(self, item_id: str) -> None:
        print(f"选中: {item_id}")
```

### 7.4 Session 关闭链路

```
QML closePlugin("my-tool")
  → LauncherBridge.closePlugin(plugin_id)
  → pluginClosed.emit(plugin_id)
  → main.py: session_mgr.close_plugin(plugin_id)
  → PluginSessionManager.close_plugin():
      1. session = self._sessions.pop(plugin_id)     # 移除会话引用
      2. setContextProperty(contextProperty, None)    # QML 上下文清空
      3. session.close()                              # dispose() + deleteLater()
      4. plugin_manager.close_runtime(plugin_id)      # runtime.on_exit()
```

---

## 8. ViewModel：MVVM 架构中的业务桥

### 8.1 ViewModel 职责

ViewModel 是 QML 和 Service 之间的桥梁：

```
QML (View) ──调用──> ViewModel (@Slot) ──委托──> Service (纯 Python)
QML (View) <──绑定── ViewModel (@Property) <──结果── Service
```

### 8.2 @Property：QML 读取 Python 数据

```python
from PySide6.QtCore import Property, Signal

class MyViewModel(QObject):
    countChanged = Signal()
    itemsChanged = Signal()

    def __init__(self):
        super().__init__()
        self._items: list[dict] = []
        self._count: int = 0

    # getter / setter / notify
    def _get_count(self) -> int:
        return self._count

    def _set_count(self, value: int):
        if self._count != value:
            self._count = value
            self.countChanged.emit()

    count = Property(int, _get_count, _set_count, notify=countChanged)

    # 只读属性
    items = Property("QVariantList", lambda self: self._items, notify=itemsChanged)
```

QML 中直接绑定：

```qml
Text { text: myToolVm.count }                       // 读
Button { onClicked: myToolVm.count = myToolVm.count + 1 }  // 写
ListView { model: myToolVm.items }                   // 绑定列表
```

### 8.3 @Slot：QML 调用 Python 方法

```python
from PySide6.QtCore import Slot

@Slot(str, int)
def updateItem(self, name: str, index: int) -> None:
    if 0 <= index < len(self._items):
        self._items[index]["name"] = name
        self.itemsChanged.emit()

@Slot(result=str)
def getInitialText(self) -> str:
    return self._initial_text
```

QML 调用：

```qml
myToolVm.updateItem(input.text, listView.currentIndex)
```

### 8.4 Signal：Python 通知 QML

```python
class MyViewModel(QObject):
    dataProcessed = Signal(str, "QVariantMap")
    errorOccurred = Signal(str)

    @Slot(str)
    def process(self, text: str) -> None:
        try:
            result = self._service.process(text)
            self.dataProcessed.emit("成功", result)
        except Exception as e:
            self.errorOccurred.emit(str(e))
```

QML 接收：

```qml
Connections {
    target: myToolVm
    function onDataProcessed(message, data) { ... }
    function onErrorOccurred(error) { statusLabel.text = error }
}
```

### 8.5 dispose()：清理资源

```python
def dispose(self) -> None:
    """在 Session 关闭时调用，停止任务、Timer、连接等资源。"""
    if hasattr(self, '_service'):
        self._service.close()  # 如果有需要关闭的资源
```

**重要**：每次修改代码时，检查你的 ViewModel 是否有 `dispose()` 方法。不要盲目 `disconnect()` 所有 Signal；未连接的 Signal 在 PySide6 中可能打印 RuntimeWarning。通常只需要停止后台任务、Timer，并关闭 Service 资源。

---

## 9. Service：纯 Python 业务层

### 9.1 Service 是什么

Service 是**纯 Python 类**，不依赖 `QObject`、`Signal`、`Slot`。它只做业务逻辑：

```python
class MyService:
    def __init__(self):
        self._data = {}

    def process(self, input_text: str) -> dict:
        result = self._heavy_computation(input_text)
        self._data[input_text] = result
        return result

    def _heavy_computation(self, text: str) -> dict:
        # 复杂算法、IO、网络请求、数据库操作
        return {"processed": text, "length": len(text)}
```

### 9.2 为什么需要 Service 层

| 写在哪 | 适合什么 | 不适合什么 |
|--------|---------|-----------|
| QML | 布局、绑定、简单显示逻辑 | 数据解析、文件 IO、网络请求、数据库 |
| ViewModel | QML ↔ Python 通信、UI 状态管理 | 复杂算法、可复用业务逻辑 |
| Service | 纯业务逻辑、算法、IO、数据库 | QML 通信（不需要 `QObject` 继承） |

### 9.3 本项目中的 Service 示例

```
src/features/api_test/service.py      # HTTP 请求、数据库、WS 连接
src/features/qr/service.py             # 二维码生成和扫描
src/features/clipboard/service.py      # 剪切板监听、SQLite 存储
src/features/json_parser/service.py    # JSON 格式化、JSONPath
```

### 9.4 ViewModel 委托 Service 的标准模式

```python
class MyViewModel(QObject):
    resultReady = Signal(str)

    def __init__(self, service: MyService):
        super().__init__()
        self._service = service

    @Slot(str)
    def process(self, text: str) -> None:
        # ViewModel 做参数校验和 QML 通信
        if not text.strip():
            self.resultReady.emit("输入不能为空")
            return
        # Service 做真正的处理
        result = self._service.process(text)
        self.resultReady.emit(result["processed"])
```

---

## 10. QML 页面开发

### 10.1 基本模板

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../app/ui"      // 通用 UI 组件
import "../../app/theme"   // 主题
import "components"        // 本插件子组件

Item {
    id: root
    readonly property bool dark: app.theme === "dark"

    // 界面...
}
```

### 10.2 必须使用的通用组件

插件页面**不应该**自己写原始 `Button`、`TextField`，而是用框架提供的：

```qml
UiButton { text: "确定"; dark: root.dark; variant: "primary" }
UiTextField { dark: root.dark; placeholderText: "输入" }
UiTextArea { dark: root.dark; readOnly: true }
UiSwitch { dark: root.dark; checked: someValue }
UiComboBox { dark: root.dark; model: [...] }
UiCheckBox { dark: root.dark; checked: someValue }
UiIcon { name: "mdi6.star"; color: "#fff"; iconSize: 20 }
```

### 10.3 主题系统

所有颜色通过 `Theme.token(name, dark)` 获取：

```qml
readonly property color textMain: Theme.token("color-text-primary", dark)
readonly property color panelBg: Theme.token("color-bg-surface", dark)
```

不要硬编码颜色值。这样可以保证深浅色主题自动切换。

### 10.4 访问 ViewModel

```qml
// plugin.json: "contextProperty": "myToolVm"
// QML 直接使用这个变量名：
onClicked: myToolVm.process(input.text)
text: myToolVm.count
```

### 10.5 QML 组件拆分原则

| 场景 | 做法 |
|------|------|
| 需要在多处复用 | 抽成独立 `.qml` 文件，通过 `property` 接收数据，`signal` 发出事件 |
| 单页使用但超过 200 行 | 抽成独立文件，放在 `components/` 目录 |
| 通用 UI 组件 | 放在 `src/app/ui/`，整个项目复用 |

```qml
// KvTableSection.qml — 通过 property/signal 通信
ColumnLayout {
    property var rows: []
    signal rowKeyCommitted(int index, string keyText)

    Repeater {
        model: root.rows
        delegate: ApiKvRow {
            onKeyCommitted: root.rowKeyCommitted(index, keyText)
        }
    }
}
```

---

## 11. launchMode 详解

| 模式 | UI 形态 | 关闭时机 | 典型插件 |
|------|---------|---------|---------|
| `inline_view` | 嵌入 Launcher 输入框下方 | 按 Esc 或失焦 | JSON 解析、二维码、剪切板 |
| `window` | 独立原生窗口 | 用户关窗 | API 测试、下载工具 |
| `list` | Launcher 内列表模式 | 按 Esc | 软件快速启动 |
| `none` | 无 UI，执行后消失 | 立即关闭 Session | 重启应用 |

### 11.1 inline_view 开发要点

- 页面根元素必须是 `Item`（不是 `Window`）
- 页面必须提供 `activateSelection()` 和 `moveSelection(delta)` 函数，供键盘导航
- 页面宽度取自 Launcher 宽度，不需要自己设

### 11.2 window 开发要点

- 页面根元素仍是 `Item`，框架用 `PluginWindow.qml` 做外壳
- 窗口大小由 Manifest 的 `window` 字段控制
- 用户关窗 → `closing` 信号 → `session_mgr.close_plugin()`

### 11.3 list 开发要点

- Session 必须重写 `list_model()` 返回 `[{"id":..., "title":..., ...}]`
- `on_input_changed(text)` 返回过滤后的列表
- `on_list_item_selected(item_id)` 处理选中

---

## 12. background 后台插件

### 12.1 什么是后台插件

后台插件在应用启动时就开始运行（不创建 UI），持续在后台提供服务。用户打开时才创建 UI Session。关闭 UI 不影响后台服务继续运行。

### 12.2 必须实现的方法

```python
class MyBackgroundRuntime:
    def on_background_start(self, ctx: PluginContext) -> None:
        """应用启动时调用。创建后台服务并注册。"""
        self._service = MyBackgroundService()
        ctx.services["my.bg.key"] = self._service

    def on_enter(self, ctx, action) -> PluginSession:
        """用户打开时调用。创建 ViewModel（引用后台服务）"""
        service = ctx.services.get("my.bg.key")
        view_model = MyWindowViewModel(service)
        return QmlPluginSession(action.manifest, "inline_view", view_model)

    def on_background_stop(self) -> None:
        """应用退出时调用。关闭后台服务。"""
        if self._service:
            self._service.close()

    def on_exit(self) -> None:
        """UI Session 关闭时调用。后台服务不受影响。"""
        pass
```

### 12.3 关键行为

- `PluginManager.close_runtime()` **不会**关闭 `activation == "background"` 的 Runtime
- 后台 Runtime 只在整个应用退出时由 `BackgroundManager.stop_all()` 关闭
- 后台 Service 通过 `ctx.services` 共享，其他插件可以访问

### 12.4 剪切板插件 —— 完整案例

```python
# runtime.py — ClipboardRuntime
class ClipboardRuntime:
    def on_background_start(self, ctx):
        db_path = _clipboard_data_dir() / "clipboard.db"
        self._service = ClipboardBackgroundService(db_path)
        ctx.services["clipboard.background"] = self._service

    def on_enter(self, ctx, action):
        service = ctx.services["clipboard.background"]
        return ClipboardInlineSession(action.manifest,
            ClipboardWindowViewModel(service))

    def on_background_stop(self):
        if self._service:
            self._service.close()
```

---

## 13. 上下文推荐 Matchers

### 13.1 工作原理

框架为每条输入生成 `LauncherContext`：

```python
@dataclass
class LauncherContext:
    input_text: str                    # 完整输入文本
    input_body: str                    # 去掉前缀后的文本
    prefix: str                        # 识别到的前缀
    detected_input_kinds: frozenset    # 检测到的文本类型: {"json", "url", ...}
    clipboard_text: str                # 剪切板文本
    detected_clipboard_kinds: frozenset  # 剪切板类型
```

### 13.2 Matcher 声明

插件在 Manifest 中声明自己对什么上下文敏感：

```json
"matchers": [
    {"source": "input",     "kind": "json",       "boost": 180},
    {"source": "input",     "kind": "url",        "boost": 120},
    {"source": "clipboard", "kind": "image",      "boost": 160},
    {"source": "clipboard", "kind": "image_file", "boost": 130},
    {"source": "input",     "kind": "regex",      "boost": 150, "pattern": "^\\d{17}[\\dXx]$"}
]
```

### 13.3 支持的 kind

| kind | 说明 | 匹配源 |
|------|------|--------|
| `json` | 文本能解析为 JSON | input, clipboard |
| `url` | 文本是 URL | input, clipboard |
| `file` | 文本/剪切板内容是文件路径 | input, clipboard |
| `image` | 剪切板原生图片 | clipboard |
| `image_file` | 文件扩展名是图片 | input, clipboard |
| `clipboard` | 剪切板任意内容 | clipboard |
| `text` | 普通文本 | input |
| `regex` | 正则匹配，需配合 `pattern` | input |

### 13.4 完整示例

```json
// api_test/plugin.json
"matchers": [
    {"source": "input",     "kind": "url", "boost": 120},
    {"source": "clipboard", "kind": "url", "boost": 70}
]
```

效果：输入 URL 或剪切板有 URL 时，API 测试插件排在前面。

```json
// image_compress/plugin.json
"matchers": [
    {"source": "input",     "kind": "image_file", "boost": 180},
    {"source": "clipboard", "kind": "image",      "boost": 160},
    {"source": "clipboard", "kind": "image_file", "boost": 130}
]
```

效果：图片文件出现时图片压缩插件排序最高。

---

## 14. 前缀系统

### 14.1 前缀是什么

用户在启动器中输入 `json {"foo": 1}` 时：
- `json` 被识别为**前缀**（选择 JSON 插件）
- `{"foo": 1}` 是**业务输入**

### 14.2 前缀声明

```json
"prefixes": ["json", "jq"]
```

多个前缀都可以激活同一个插件。

### 14.3 内置插件前缀速查

| 前缀 | 插件 |
|------|------|
| `json`, `jq` | JSON 解析 |
| `qr`, `qrcode` | 二维码 |
| `api`, `http` | API 测试 |
| `img`, `image` | 图片压缩 |
| `clip`, `clipboard` | 剪切板历史 |
| `down`, `download` | 下载工具 |
| `case` | 文本大小写 |

### 14.4 前缀 vs 业务输入

```text
用户输入:  json {"foo": 1}
解析:      prefix="json", input_body='{"foo": 1}'
结果:      JSON 插件被选中，input_text=""（前缀命中时不传业务文本）

用户输入:  {"foo": 1}
解析:      prefix="" (空), detected_input_kinds={"json"}
结果:      JSON 插件因 matcher 高亮，input_text='{"foo": 1}' 传给插件
```

---

## 15. 动态命令

### 15.1 什么是动态命令

运行时注册的命令，不需要修改 Manifest。用于：
- 下载插件：有未完成任务时贡献"打开下载任务"
- API 插件：贡献最近的请求记录
- 任何运行时状态变化

### 15.2 注册和取消

```python
ctx.platform.commands.register(
    "download.pause_all",
    title="暂停所有下载",
    subtitle="暂停当前活跃的下载任务",
    icon="qta:mdi6.pause",
    launch_mode="none",
    order=50,
)

# 取消注册
ctx.platform.commands.unregister("download.pause_all")
```

`ctx.dynamic_commands` 仍可作为旧代码兼容入口，但新插件不要再直接依赖它。

### 15.3 DynamicCommand 字段

```python
@dataclass
class DynamicCommand:
    plugin_id: str
    command_id: str
    title: str
    subtitle: str = ""
    icon: str = ""
    keywords: list[str] = field(default_factory=list)
    prefixes: list[str] = field(default_factory=list)
    matchers: list[ContextMatcher] = field(default_factory=list)
    launch_mode: LaunchMode = "none"
    order: int = 99
    payload: dict = field(default_factory=dict)
```

---

## 16. 插件间通信

### 16.1 通过 ctx.services

```python
# 后台插件注册服务
ctx.services["clipboard.background"] = self._service

# 其他插件读取
service = ctx.services.get("clipboard.background")
if service:
    latest = service.store.latest_item()
```

### 16.2 通过 manifest.json 声明依赖（建议）

```json
{
  "id": "my-tool",
  "dependencies": {
    "clipboard": ">=1.0.0"
  }
}
```

当前版本尚未强制校验依赖，但建议在 Manifest 中声明。

### 16.3 最佳实践

- **优先用 `ctx.platform`**：系统能力、存储、动态命令都走统一入口
- **`ctx.services` 用于插件间共享服务**：例如 `clipboard.background`
- **避免直接 import**：不要在插件 A 里 `import src.features.plugin_b.service`
- **服务 key 使用反向域名风格**：`"clipboard.background"` 而不是 `"clip"`

不要直接写这些调用：

```python
QApplication.clipboard()
QFileDialog.getOpenFileName(...)
StorageManager()
os.startfile(...)
```

---

## 17. 资源清理

### 17.1 清理清单

| 资源类型 | 清理方式 | 在哪清理 |
|---------|---------|---------|
| Signal 连接 | 只断开你显式保存的外部连接 | `ViewModel.dispose()` |
| QTimer | `.stop(); .deleteLater()` | `ViewModel.dispose()` |
| 线程 | 设置停止标志 + `thread.join()` | `ViewModel.dispose()` |
| SQLite 连接 | `conn.close()` 或使用 `with` 语句 | Service |
| WebSocket | `.close()` | Service / ViewModel.dispose() |
| QML Context | `setContextProperty(name, None)` | `PluginSessionManager.close_plugin()` |
| Runtime 引用 | `runtimes.pop(plugin_id)` | `PluginManager.close_runtime()` |
| Python QObject | `.deleteLater()` | `QmlPluginSession.close()` |

### 17.2 dispose() 标准模板

```python
class MyViewModel(QObject):
    def dispose(self) -> None:
        """在 QmlPluginSession.close() 中自动调用。"""
        self._disposed = True

        if hasattr(self, '_runner') and self._runner:
            self._runner.cancel_all()

        if hasattr(self, '_service') and self._service:
            close_fn = getattr(self._service, 'close', None)
            if close_fn:
                close_fn()

        if hasattr(self, '_timer') and self._timer:
            self._timer.stop()
            self._timer.deleteLater()
```

### 17.3 验证清理是否完整

1. 反复开关插件 10 次，内存不应持续增长
2. 检查控制台有无 `[WARN] 插件 Session 关闭失败`
3. 检查信号是否重复连接（同一操作触发多次）
4. WebSocket 连接是否被关闭（netstat 确认）

---

## 18. 插件验收清单

每个插件提交前检查：

- [ ] `plugin.json` 格式正确，所有必需字段齐全
- [ ] `id` 全局唯一（kebab-case）
- [ ] `entrypoint` 指向存在的模块和函数
- [ ] `contextProperty` 与 QML 中使用的变量名一致
- [ ] `qmlPage` 路径正确，相对于插件目录
- [ ] 读取 Manifest 不触发 Python import（非后台插件的 Runtime 未加载）
- [ ] QML 页面能独立加载（`QQmlComponent.isError()` 返回 false）
- [ ] QML 使用 `UiButton`、`UiTextField` 等通用组件，不自己写原始 Qt 控件
- [ ] QML 不硬编码颜色值（使用 `Theme.token()`）
- [ ] ViewModel 有 `dispose()` 方法，清理了所有 Signal、Timer、线程
- [ ] 非后台插件关闭后 Session 正确清理（无内存泄漏）
- [ ] 插件错误不导致 Launcher 崩溃（异常被捕获）
- [ ] `keywords` 包含中文、英文，覆盖常用搜索词
- [ ] `launchMode` 合理（inline 优先，window 用于复杂工具）
- [ ] 启动应用后手动验证搜索、打开、关闭和资源释放

---

## 19. 故障排查

### 插件搜索不到

```powershell
# 检查清单是否正确加载
uv run python -c "
import sys; sys.path.insert(0, 'src')
from app.plugins.manifest_loader import load_all_plugin_manifests
for m in load_all_plugin_manifests():
    print(f'{m.id}')
"
```

常见原因：
- `plugin.json` 不在 `src/features/*/` 或 `plugins/*/` 下
- `id` 与其他插件重复（框架会跳过后加载的）
- JSON 语法错误（框架打印 `[WARN] 插件 Manifest 加载失败`）

### QML 页面加载失败

```python
from PySide6.QtQml import QQmlComponent
c = QQmlComponent(engine, QUrl.fromLocalFile("YourPage.qml"))
if c.isError():
    for e in c.errors():
        print(e.toString())
```

常见原因：
- import 路径错误（相对路径的层数不对）
- 缺少 `import "../../app/ui"` 或 `import "../../app/theme"`
- 引用不存在的变量（检查 `contextProperty` 是否匹配）
- 括号不匹配（QML 编译器会精确报告行号）

### Signal/Slot 不通

```python
# 检查 Slot 是否加了装饰器
@Slot(str)          # ✓ 正确
def process(self, text): ...

def process(self, text):  # ✗ QML 调不到
```

### 插件关闭后内存不下

检查：
- `ViewModel.dispose()` 是否存在且被调用？
- Service 是否有关闭数据库/文件/网络连接？
- 是否停止了后台任务、Timer 或热键监听？
- 不要盲目断开所有 Signal；未连接的 Signal 可能打印 RuntimeWarning。

---

## 20. 附录：内置插件速查

| 插件 ID | 名称 | launchMode | activation | 特点 |
|---------|------|-----------|------------|------|
| `json-parser` | JSON 解析 | inline_view | lazy | 简单完整插件，学习起点 |
| `qr-code` | 二维码 | inline_view | lazy | ViewModel + Service 分层 |
| `image-compress` | 图片压缩 | inline_view | lazy | 使用 ctx.services 获取剪切板 |
| `api-test` | API 测试 | window | lazy | 最复杂插件，全功能 MVVM |
| `clipboard` | 剪切板 | inline_view | **background** | 后台服务 + 懒 UI |
| `download` | 下载工具 | window | lazy | 窗口模式参考 |
| `app-launcher` | 软件快速启动 | list | lazy | list 模式参考 |
| `packet-capture` | 网络抓包 | window | lazy | 窗口模式 |
| `system-settings` | 系统设置 | inline_view | lazy | 无 contextProperty |
| `about` | 关于 | inline_view | lazy | 多 Manifest 共享 Runtime |

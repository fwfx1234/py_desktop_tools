# PyQt/PySide6 + QML 新手教程：读懂并掌握本项目

本文档面向第一次系统学习 PyQt/PySide6 的同学。目标不是只告诉你“这里用了什么库”，而是带你把当前项目从启动、界面、信号通信、插件机制、后台服务到测试验证串起来。

项目会继续演进，所以这是一份“随项目同步更新”的活文档。以后新增插件、重构架构或引入新技术时，请优先更新本文对应章节。

## 0. 先建立全局地图

本项目是一个类 uTools 的桌面工具箱：

- Python 负责启动应用、业务逻辑、插件管理、数据库、剪切板、热键、系统托盘。
- QML 负责界面，包括启动器窗口、插件页面、通用 UI 组件。
- PySide6 是 Python 和 Qt/QML 之间的桥。
- 插件通过 `plugin.json` 声明自己，只有被启动时才加载真正的 Python Runtime 和 QML 页面。

核心入口：

```text
src/app/main.py
```

核心界面：

```text
src/app/Main.qml
src/app/launcher/LauncherWindow.qml
src/app/launcher/PluginWindow.qml
```

插件目录：

```text
src/features/
```

建议你先记住一句话：

> `main.py` 创建 Qt 应用和 QML 引擎，`LauncherWindow.qml` 显示搜索框，`LauncherBridge` 负责把 QML 的搜索和启动请求交给 Python，插件 Runtime 再创建 ViewModel 给插件 QML 使用。

## 1. 本项目用到的技术栈

### Python 与工程管理

文件：`pyproject.toml`

项目使用 Python 3.10+，依赖通过 `pyproject.toml` 声明：

- `PySide6`：Qt 的 Python 绑定，本项目的桌面应用基础。
- `pyside6-addons`：额外 Qt 模块。
- `qtawesome`：图标库，让 QML/Python 可以使用 FontAwesome、Material Design Icons 等图标。
- `qrcode`、`Pillow`、`opencv-python`：二维码生成、图片处理和二维码扫描。
- `pyperclip`：文本剪切板读写。
- `requests`、`websocket-client`：API 测试插件的网络能力。
- `PyYAML`：读取 OpenAPI/YAML 等结构化数据。
- `pypinyin`：中文命令的拼音搜索。
- `pylnk3`：Windows 快捷方式相关能力。

`pyproject.toml` 里还有入口：

```toml
[project.scripts]
app = "app.main:main"
```

意思是安装或通过 `uv run` 运行后，可以执行：

```powershell
uv run app
```

### Qt、PySide6、QML 的关系

你可以这样理解：

```text
Qt      = 底层跨平台桌面框架
PySide6 = Python 调 Qt 的桥
QML     = Qt Quick 的声明式界面语言
```

本项目不是传统的 `QWidget` 写法，而是：

```text
Python QObject/ViewModel + QML 界面
```

也就是说，界面写在 `.qml` 文件里，业务对象写在 `.py` 文件里。QML 通过 Python 暴露出来的 `Property`、`Signal`、`Slot` 与业务逻辑互动。

### 架构风格

项目主要采用：

- MVVM：QML 是 View，Python 的 `QObject` 是 ViewModel，纯 Python 类是 Service。
- 插件化：每个功能目录通过 `plugin.json` 声明自己。
- 懒加载：普通插件不在应用启动时创建 ViewModel，只有用户打开时才创建。
- 后台插件：剪切板插件应用启动后常驻监听，但 UI 仍然懒加载。

## 2. 如何运行和验证

推荐从项目根目录运行：

```powershell
uv run app
```

运行后应用默认常驻后台，按：

```text
Alt+Space
```

唤起启动器窗口。

剪切板历史默认快捷键：

```text
Alt+V
```

项目已经移除旧的 `tools/feature_smoke.py`。当前验证以两类方式为主：

```powershell
uv run python -m compileall src
uv run app
```

先做 Python 语法/导入层面的静态检查，再启动应用手动验证启动器搜索、插件打开、窗口关闭、后台监听等关键链路。

## 3. 项目目录怎么读

当前核心目录：

```text
src/
  app/
    main.py
    Main.qml
    app_view_model.py
    commands/
    hotkey/
    launcher/
    plugins/
    theme/
    tray/
    ui/
  features/
    api_test/
    app_launcher/
    clipboard/
    download/
    image_compress/
    json_parser/
    packet_capture/
    qr/
    system/
```

### `src/app`

这是应用框架层。它不应该关心某个具体插件的业务细节。

重点文件：

- `main.py`：应用启动总入口。
- `Main.qml`：加载启动器窗口。
- `app_view_model.py`：全局应用状态，目前主要是主题。
- `launcher/LauncherWindow.qml`：Alt+Space 唤起的搜索窗口。
- `launcher/launcher_bridge.py`：QML 调 Python 的启动器桥。
- `launcher/PluginWindow.qml`：独立窗口插件的外壳。
- `commands/command_service.py`：搜索、排序、系统命令和系统应用。
- `commands/context.py`：识别输入文本类型，例如 JSON、URL、图片路径。
- `plugins/manifest_loader.py`：扫描并解析插件清单。
- `plugins/plugin_manager.py`：按需加载插件 Runtime。
- `plugins/session_manager.py`：管理插件会话和 QML 上下文对象。
- `plugins/background_manager.py`：启动/停止后台插件。
- `hotkey_coordinator.py`：协调启动器、剪切板、插件的全局热键注册和重注册。
- `tray/system_tray_manager.py`：系统托盘。

### `src/features`

这是功能插件层。每个目录通常包含：

```text
plugin.json
runtime.py
view_model.py
service.py
SomePage.qml
```

不是每个插件都有全部文件。比如 JSON 插件逻辑很小，没有单独的 `service.py`；二维码插件有生成和扫描逻辑，所以有 `service.py`。

## 4. 从启动流程开始理解

文件：`src/app/main.py`

启动流程可以按这 7 步读：

1. 设置 Qt Quick Controls 样式。
2. 创建 `QApplication`。
3. 创建 `QQmlApplicationEngine`。
4. 创建全局对象，比如 `AppViewModel`、命令服务、插件管理器、启动器桥。
5. 加载 `Main.qml`，进而显示 `LauncherWindow`。
6. 注册全局热键和系统托盘。
7. 进入 Qt 事件循环。

简化后的逻辑像这样：

```python
def main() -> int:
    QQuickStyle.setStyle("Basic")
    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)

    engine = QQmlApplicationEngine()
    app_vm = AppViewModel()

    ctx = engine.rootContext()
    ctx.setContextProperty("app", app_vm)

    manifests = load_all_plugin_manifests()
    plugin_manager = PluginManager(manifests)
    command_service = CommandService(...)
    bridge = LauncherBridge(command_service, ...)
    ctx.setContextProperty("launcherBridge", bridge)

    engine.load(QUrl.fromLocalFile(str(main_qml)))
    return qt_app.exec()
```

这里有三个新手必须理解的概念。

### `QApplication`

`QApplication` 是 Qt 应用对象。所有窗口、事件、剪切板、托盘都依赖它。

本项目设置了：

```python
qt_app.setQuitOnLastWindowClosed(False)
```

这表示窗口关闭后应用不退出，而是常驻后台。这符合启动器工具的产品形态。

### `QQmlApplicationEngine`

它负责加载 QML：

```python
engine.load(QUrl.fromLocalFile(str(main_qml)))
```

QML 文件不是 Python 直接 import 的，而是由 QML 引擎加载。

### `setContextProperty`

这是 Python 对象暴露给 QML 的关键。

例如：

```python
ctx.setContextProperty("app", app_vm)
ctx.setContextProperty("launcherBridge", bridge)
```

这样 QML 里就可以直接访问：

```qml
app.theme
launcherBridge.performSearch(text)
launcherBridge.searchResults
```

## 5. QML 是怎么写界面的

文件：`src/app/Main.qml`

现在它非常短：

```qml
import QtQuick
import "theme"
import "launcher"

LauncherWindow {
    objectName: "launcherWindow"
    visible: false
}
```

意思是应用启动后创建一个 `LauncherWindow`，但默认不显示。之后按 `Alt+Space` 时，Python 会调用这个窗口的 `show()`。

### QML 的基本语法

以 `LauncherWindow.qml` 为例：

```qml
Window {
    id: launcher
    width: 800
    height: 600
    color: "transparent"

    property bool mixedMode: false

    function exitMixedMode() {
        mixedMode = false
    }
}
```

常见语法：

- `Window { ... }`：创建一个窗口对象。
- `id: launcher`：给当前对象起一个 QML 内部名字。
- `property bool mixedMode: false`：声明属性。
- `function exitMixedMode() { ... }`：声明函数。
- `anchors.fill: parent`：布局锚定到父元素。
- `Layout.fillWidth: true`：在 Layout 中填满宽度。
- `onTextChanged: ...`：响应信号。

### QML 中的绑定

QML 的属性可以绑定表达式：

```qml
readonly property bool dark: typeof app !== "undefined" && app ? app.theme === "dark" : false
```

这表示 `dark` 会跟随 `app.theme` 变化。

### QML 调 Python

在搜索框里：

```qml
onTextChanged: {
    if (mixedMode && mixedPluginId) {
        launcherBridge.setPluginInput(mixedPluginId, text)
    } else {
        launcherBridge.performSearch(text)
    }
}
```

这里的 `launcherBridge` 是 Python 中注入的 `LauncherBridge` 对象。QML 调用它的方法，本质上是在调用 Python 中用 `@Slot` 暴露的方法。

## 6. Python 如何暴露给 QML

文件：`src/app/launcher/launcher_bridge.py`

PySide6 中，让 QML 能访问 Python 对象，需要继承 `QObject`：

```python
class LauncherBridge(QObject):
    searchCompleted = Signal()
```

### `Signal`

信号用来通知 QML：“数据变了，你该刷新了”。

例如：

```python
searchCompleted = Signal()
```

当搜索结果更新后：

```python
self.searchCompleted.emit()
```

QML 中依赖这个信号的属性会刷新。

### `Property`

属性用来让 QML 读取 Python 数据：

```python
@Property("QVariantList", notify=searchCompleted)
def searchResults(self) -> list[dict]:
    return self._results
```

QML 可以直接读取：

```qml
model: launcher.safeSearchResults
```

而 `safeSearchResults` 又来自：

```qml
readonly property var safeSearchResults: hasBridge ? launcherBridge.searchResults : []
```

### `Slot`

槽是 QML 可以调用的方法：

```python
@Slot(str)
def performSearch(self, query: str) -> None:
    ...
```

QML 调用：

```qml
launcherBridge.performSearch(text)
```

新手可以先记住：

```text
Signal   = Python 通知 QML
Property = QML 读取 Python 数据
Slot     = QML 调 Python 方法
```

## 7. 启动器搜索是怎么工作的

相关文件：

```text
src/app/launcher/LauncherWindow.qml
src/app/launcher/launcher_bridge.py
src/app/commands/command_service.py
src/app/commands/context.py
```

输入框文字变化后：

```text
QML TextField.onTextChanged
  -> launcherBridge.performSearch(text)
  -> CommandService.search(query, context)
  -> 生成 searchResults
  -> searchCompleted.emit()
  -> QML ListView 刷新
```

### 搜索结果来自哪里

`CommandService` 合并这些来源：

- 插件 `plugin.json` 中声明的命令。
- 插件运行时注册的动态命令。
- 系统命令，比如记事本、任务管理器、重启应用。
- Windows 应用快捷方式。
- 使用次数和最近使用记录。

### 输入上下文识别

文件：`src/app/commands/context.py`

它会识别输入是不是：

- JSON
- URL
- 文件路径
- 图片文件路径
- 普通文本

例如你输入：

```text
{"foo": 1}
```

`detect_text_kinds()` 会识别为：

```text
text + json
```

于是 JSON 插件的 matcher 会加分。

如果你输入：

```text
https://example.com
```

二维码插件和 API 测试插件都会因为 `url` matcher 获得推荐分。

### 前缀命令

每个插件可以声明前缀：

```json
"prefixes": ["json", "jq"]
```

当输入：

```text
json {"foo": 1}
```

启动器会把 `json` 当成“选择 JSON 插件的命令词”，而不是业务输入。当前项目设计中，前缀命中时传给插件的 `input_text` 是空字符串。

如果直接输入：

```text
{"foo": 1}
```

这才会被作为业务内容传给 JSON 插件。

这个区别很重要：

```text
json {...}     = 用前缀明确选择插件
{...}          = 输入内容本身被识别为 JSON，并传给插件处理
```

## 8. 插件清单 `plugin.json`

以 JSON 插件为例：

文件：`src/features/json_parser/plugin.json`

```json
{
  "id": "json-parser",
  "name": "JSON 解析",
  "entrypoint": "runtime:create_runtime",
  "qmlPage": "JsonParserPage.qml",
  "contextProperty": "jsonParserVm",
  "commands": [
    {
      "id": "json-parser.open",
      "title": "JSON 解析",
      "prefixes": ["json", "jq"],
      "launchMode": "inline_view",
      "matchers": [
        {"source": "input", "kind": "json", "boost": 180}
      ]
    }
  ]
}
```

关键字段：

- `id`：插件唯一标识。
- `name`：显示名称。
- `entrypoint`：Runtime 工厂函数，格式是 `模块名:函数名`。
- `qmlPage`：插件页面。
- `contextProperty`：插件 ViewModel 注入到 QML 的名字。
- `activation`：`lazy` 或 `background`。
- `commands`：贡献给启动器搜索的命令。
- `launchMode`：启动方式。
- `matchers`：上下文推荐规则。

### 插件启动方式

当前支持：

| launchMode | 说明 | 例子 |
| --- | --- | --- |
| `none` | 无界面，执行后结束 | 重启应用 |
| `list` | 使用启动器通用列表 | 软件快速启动 |
| `inline_view` | 嵌入启动器窗口 | JSON、二维码、剪切板、图片压缩 |
| `window` | 独立窗口 | API 测试、下载工具 |

### 插件激活方式

`activation` 不等于 `launchMode`。

```text
activation = 插件什么时候加载 Runtime
launchMode = 插件启动后以什么 UI 形式展示
```

例如剪切板：

```json
"activation": "background",
"launchMode": "inline_view"
```

意思是：

- 应用启动后加载后台 Runtime，用来监听系统剪切板。
- 用户打开剪切板历史时，再创建内嵌 UI。

## 9. 插件 Runtime 和 Session

相关文件：

```text
src/app/plugins/plugin_manager.py
src/app/plugins/session_manager.py
src/app/plugins/runtime.py
```

### Runtime 是什么

Runtime 是插件真正开始运行的 Python 对象。Manifest 只是静态声明，读取 Manifest 不会创建 ViewModel，也不会加载 QML 页面。

以 JSON 插件为例：

文件：`src/features/json_parser/runtime.py`

```python
class JsonParserRuntime:
    def on_enter(self, ctx: PluginContext, action: PluginAction) -> QmlPluginSession:
        view_model = JsonParserViewModel(action.input_text)
        return JsonParserSession(action.manifest, view_model)
```

当用户启动 JSON 插件时：

```text
PluginManager 加载 runtime.py
  -> 调用 create_runtime()
  -> 得到 JsonParserRuntime
  -> 调用 on_enter(...)
  -> 创建 JsonParserViewModel
  -> 返回 JsonParserSession
```

### Session 是什么

Session 表示“一次插件打开后的会话”。

它负责：

- 暴露 QML context。
- 返回要加载的 QML 页面。
- 接收启动器输入变化。
- 关闭时释放 ViewModel、信号、Timer、线程、数据库连接等资源。

项目提供了通用的 `QmlPluginSession`：

```python
class QmlPluginSession:
    def create_qml_context(self) -> dict[str, QObject]:
        if self._view_model is None or not self.manifest.context_property:
            return {}
        return {self.manifest.context_property: self._view_model}
```

也就是说，如果插件清单写了：

```json
"contextProperty": "jsonParserVm"
```

Session 就会把 ViewModel 以 `jsonParserVm` 这个名字注入 QML。

## 10. ViewModel：Python 与 QML 的业务桥

以 JSON 插件为例：

文件：`src/features/json_parser/view_model.py`

```python
class JsonParserViewModel(QObject):
    jsonProcessed = Signal(str, str)
    jsonCopied = Signal(bool, str)
    inputTextChanged = Signal(str)

    @Slot(str, str)
    def processJson(self, jsonText: str, query: str) -> None:
        text, error = self._process(jsonText, query)
        self.jsonProcessed.emit(text, error)
```

QML 页面调用：

文件：`src/features/json_parser/JsonParserPage.qml`

```qml
function runParse() {
    jsonParserVm.processJson(input.text, query.text)
}
```

Python 处理完后发信号：

```python
self.jsonProcessed.emit(text, error)
```

QML 接收信号：

```qml
Connections {
    target: jsonParserVm
    function onJsonProcessed(text, errorText) {
        output.text = text
        err.text = errorText
    }
}
```

这就是本项目最典型的数据流：

```text
用户操作 QML
  -> QML 调用 ViewModel Slot
  -> Python 处理
  -> Python emit Signal
  -> QML Connections 更新界面
```

## 11. Service：把复杂业务从 ViewModel 拆出去

当业务逻辑变复杂，ViewModel 不应该什么都做。

以二维码插件为例：

```text
src/features/qr/
  QrCodePage.qml
  view_model.py
  service.py
```

`QrViewModel` 负责和 QML 通信：

```python
@Slot(str)
def generateQr(self, content: str) -> None:
    self.qrGenerated.emit(self._service.generate(content))
```

`QrService` 负责真正生成二维码：

```python
def generate(self, content: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    ...
```

这种分层的好处：

- QML 不关心二维码怎么生成。
- ViewModel 不堆太多算法和 IO。
- Service 更容易单独测试。

新手判断标准：

```text
只负责界面通信的，放 ViewModel。
可复用、有 IO、有数据库、有网络、有复杂算法的，放 Service。
```

## 12. QML 页面如何访问插件 ViewModel

以 JSON 页面为例：

```qml
Component.onCompleted: {
    input.text = jsonParserVm.initialText()
    runParse()
}
```

这里的 `jsonParserVm` 来自三处配合：

1. `plugin.json`：

```json
"contextProperty": "jsonParserVm"
```

2. `runtime.py`：

```python
view_model = JsonParserViewModel(action.input_text)
return JsonParserSession(action.manifest, view_model)
```

3. `PluginSessionManager.open_plugin()`：

```python
for name, obj in session.create_qml_context().items():
    self._qml_context.setContextProperty(name, obj)
```

所以你找一个 QML 变量从哪来，可以沿着这条链找：

```text
QML 变量名
  -> plugin.json contextProperty
  -> runtime.py 创建 ViewModel
  -> session_manager 注入 QML context
```

## 13. inline_view 插件如何嵌入启动器

文件：`src/app/launcher/LauncherWindow.qml`

启动 inline 插件时，启动器进入 `mixedMode`：

```qml
function enterPluginMode(pluginId, pluginMode, pluginInputText, clearInputAfterEnter) {
    mixedMode = true
    mixedPluginId = pluginId
    mixedPluginMode = pluginMode || "inline_view"
    ...
    mixedLoader.active = mixedPluginMode === "inline_view"
}
```

真正加载 QML 的是 `Loader`：

```qml
Loader {
    id: mixedLoader
    active: false
    source: launcher.pluginPageUrl(mixedPluginPage)
}
```

`Loader` 可以理解为“动态加载一块 QML 页面”。普通搜索状态下它不工作；进入插件模式后它才加载对应插件页面。

这就是懒加载 UI 的关键。

## 14. window 插件如何打开独立窗口

文件：

```text
src/app/main.py
src/app/launcher/PluginWindow.qml
```

独立窗口插件使用 `PluginWindow.qml` 作为外壳，再把插件页面放进去：

```python
component = QQmlComponent(engine, QUrl.fromLocalFile(str(plugin_window_qml)))
win = component.createWithInitialProperties(
    {
        "pluginId": plugin_id,
        "pluginName": manifest.name,
        "qmlPage": session.qml_page(),
        "initialWidth": window_width,
        "initialHeight": window_height,
    }
)
```

API 测试插件的 Manifest 中声明了窗口大小：

```json
"window": {
  "width": 1000,
  "height": 600
}
```

`PluginWindow.qml` 中再用 `Loader` 加载插件页面：

```qml
Loader {
    id: pageLoader
    anchors.fill: parent
    active: qmlPage.length > 0
    source: pluginWin.pluginPageUrl(qmlPage)
}
```

所以 window 插件的结构是：

```text
原生独立 Window
  -> PluginWindow.qml 外壳
  -> Loader
  -> 插件自己的 QML 页面
```

## 15. background 插件：剪切板案例

剪切板插件是本项目最适合深入学习的复杂案例。

文件：

```text
src/features/clipboard/plugin.json
src/features/clipboard/runtime.py
src/features/clipboard/service.py
src/features/clipboard/view_model.py
src/features/clipboard/ClipboardWindowPage.qml
```

### 为什么剪切板是后台插件

剪切板历史必须在用户没有打开窗口时也持续记录，所以它需要应用启动后开始监听系统剪切板。

但是 UI 不应该一启动就加载，否则浪费资源。

所以它被拆成：

```text
ClipboardBackgroundService
  常驻后台，监听剪切板，写入数据库

ClipboardWindowViewModel
  用户打开剪切板历史时才创建，读取后台服务的数据给 QML 展示
```

### 后台启动流程

`plugin.json`：

```json
"activation": "background"
```

`BackgroundManager.start_all()` 会加载所有后台插件：

```python
runtime = self._plugin_manager.ensure_runtime(manifest.id)
start = getattr(runtime, "on_background_start", None)
if callable(start):
    start(self._plugin_context)
```

剪切板 Runtime：

```python
def on_background_start(self, ctx: PluginContext) -> None:
    db_path = _clipboard_data_dir() / "clipboard.db"
    self._service = ClipboardBackgroundService(db_path)
    ctx.services[SERVICE_KEY] = self._service
```

这里把后台服务注册到了：

```python
ctx.services.clipboard
```

其他插件也可以通过这个服务读取最新剪切板内容。图片压缩插件就会用它读取剪切板里的图片文件。

### 剪切板监听

文件：`src/features/clipboard/service.py`

核心是：

```python
self._clipboard = QApplication.clipboard()
self._clipboard.dataChanged.connect(self._on_change)
```

当系统剪切板变化时，Qt 发出 `dataChanged` 信号，`ClipboardMonitor._on_change()` 会判断内容类型：

- 文件 URL
- 图片
- 文本

然后写入 SQLite。

### SQLite 存储

`ClipboardHistoryStore` 使用 `sqlite3` 管理：

- `clipboard_history`：历史记录。
- `clipboard_settings`：剪切板配置。

这种持久化服务属于 Service 层，不应该写在 QML 里。

## 16. 全局热键与系统托盘

### 全局热键

文件：`src/app/hotkey_coordinator.py`（协调层），各平台实现在 `src/app/platform/<platform>/hotkey.py`

项目通过平台 API 注册全局快捷键。以 Windows 为例，`platform/windows/hotkey.py` 使用 `RegisterHotKey`：

```python
user32.RegisterHotKey(...)
```

当系统收到热键消息时，`WinHotkeyFilter` 捕获 `WM_HOTKEY`，然后发出 Qt 信号。

`HotkeyCoordinator` 在应用启动时组装并注册所有热键。`Alt+Space` 的链路是：

```text
系统热键事件
  -> platform/windows/hotkey.py 或 platform/macos/hotkey.py
  -> HotkeyCoordinator
  -> launcher_runtime_coordinator.py toggle_launcher()
  -> QML Window show/hide
```

### 系统托盘

文件：`src/app/tray/system_tray_manager.py`

系统托盘使用：

```python
QSystemTrayIcon
QMenu
```

托盘菜单动作通过信号告诉 `main.py`：

```python
showWindowRequested = Signal()
restartRequested = Signal()
quitRequested = Signal()
```

这和 QML/ViewModel 的思路一样：不要让托盘直接操作所有东西，而是发信号，让上层决定怎么处理。

## 17. 图标系统

项目有两种图标来源：

### 资源 SVG

目录：

```text
src/app/assets/icons/
```

Manifest 里可以写：

```json
"icon": "json"
```

Python 会在内置图标目录里找 `json.svg`。

### qtawesome 图标

Manifest 或 QML 中可以写：

```text
qta:mdi6.qrcode
```

QML 不能直接调用 Python 的 `qtawesome`，所以项目实现了一个图片提供器：

文件：`src/app/qta_icon_provider.py`

```python
engine.addImageProvider("qta", QtAwesomeImageProvider())
```

QML 里通过 `image://qta/...` 访问：

```qml
source: "image://qta/mdi6.qrcode;color=8B5CF6;size=22"
```

## 18. 主题与通用 UI 组件

主题文件：

```text
src/app/theme/Theme.qml
```

通用组件：

```text
src/app/ui/
```

例如：

- `UiButton.qml`
- `UiTextField.qml`
- `UiTextArea.qml`
- `UiSwitch.qml`
- `UiComboBox.qml`
- `UiIcon.qml`

插件页面应该优先使用这些组件，而不是每个页面自己写一套按钮和输入框。

这样可以保证：

- 深浅色主题一致。
- 字体、间距、圆角、颜色一致。
- 后续改设计系统时不用改每个插件页面。

## 19. 新增一个插件的完整步骤

假设你要新增一个“文本大小写转换”插件。

### 第一步：建目录

```text
src/features/text_case/
  plugin.json
  runtime.py
  view_model.py
  TextCasePage.qml
  __init__.py
```

### 第二步：写 `plugin.json`

```json
{
  "id": "text-case",
  "name": "文本大小写",
  "version": "0.1.0",
  "description": "大小写转换、首字母大写",
  "icon": "qta:mdi6.format-letter-case",
  "entrypoint": "runtime:create_runtime",
  "qmlPage": "TextCasePage.qml",
  "contextProperty": "textCaseVm",
  "category": "tool",
  "order": 20,
  "commands": [
    {
      "id": "text-case.open",
      "title": "文本大小写",
      "subtitle": "大小写转换、首字母大写",
      "icon": "qta:mdi6.format-letter-case",
      "keywords": ["文本", "大小写", "case", "upper", "lower"],
      "prefixes": ["case"],
      "launchMode": "inline_view",
      "matchers": [
        {"source": "input", "kind": "text", "boost": 20}
      ]
    }
  ]
}
```

### 第三步：写 ViewModel

```python
from PySide6.QtCore import QObject, Signal, Slot


class TextCaseViewModel(QObject):
    converted = Signal(str)

    @Slot(str)
    def toUpper(self, text: str) -> None:
        self.converted.emit(text.upper())

    @Slot(str)
    def toLower(self, text: str) -> None:
        self.converted.emit(text.lower())
```

### 第四步：写 Runtime

```python
from app.plugins.runtime import SimpleQmlRuntime

from .view_model import TextCaseViewModel


def create_runtime() -> SimpleQmlRuntime:
    return SimpleQmlRuntime(lambda _ctx: TextCaseViewModel())
```

### 第五步：写 QML 页面

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../app/ui"
import "../../app/theme"

Item {
    readonly property bool dark: app.theme === "dark"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.s4

        UiTextArea {
            id: input
            dark: dark
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        RowLayout {
            UiButton {
                text: "大写"
                dark: dark
                onClicked: textCaseVm.toUpper(input.text)
            }
            UiButton {
                text: "小写"
                dark: dark
                onClicked: textCaseVm.toLower(input.text)
            }
        }

        UiTextArea {
            id: output
            dark: dark
            readOnly: true
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }

    Connections {
        target: textCaseVm
        function onConverted(text) {
            output.text = text
        }
    }
}
```

### 第六步：验证

运行：

```powershell
uv run python -m compileall src
```

再运行应用：

```powershell
uv run app
```

按 `Alt+Space`，搜索：

```text
文本大小写
case
```

如果搜索不到，优先检查：

- `plugin.json` 是否在 `src/features/text_case/` 下。
- `id` 是否重复。
- `entrypoint` 是否写成 `runtime:create_runtime`。
- `qmlPage` 文件名是否正确。
- `contextProperty` 是否和 QML 中使用的变量一致。

## 20. 新手最容易踩的坑

### QML 变量未定义

现象：

```text
ReferenceError: xxxVm is not defined
```

排查：

- `plugin.json` 的 `contextProperty` 是否是 `xxxVm`。
- Runtime 是否创建了对应 ViewModel。
- Session 是否返回了 `QmlPluginSession`。
- QML 页面是否在插件启动后才加载。

### Slot 没有被 QML 调到

Python 方法必须用 `@Slot` 标记：

```python
@Slot(str)
def doSomething(self, text: str) -> None:
    ...
```

如果需要返回值：

```python
@Slot(result=str)
def initialText(self) -> str:
    return self._input_text
```

### Signal 参数对不上

Python：

```python
jsonProcessed = Signal(str, str)
```

QML：

```qml
function onJsonProcessed(text, errorText) {
    ...
}
```

参数数量和顺序要对应。

### 修改 QML 后没刷新

可以开启热重载：

```bash
PY_DESKTOP_QML_HOT_RELOAD=1 uv run app
```

热重载逻辑在 `QmlHotReloader` 中。它监听 `.qml` 文件变化并重新加载根 QML。

### 插件关闭后资源没释放

如果 ViewModel 连接了信号、启动了 Timer、打开了数据库或线程，记得在 `close()` 或 `deleteLater()` 中清理。

剪切板 ViewModel 是好例子：

```python
def close(self) -> None:
    self._service.store.historyChanged.disconnect(self._emit_history)
    self._service.store.configChanged.disconnect(self._emit_config)
```

### 不要把业务逻辑写进 QML

QML 适合：

- 布局
- 绑定
- 用户交互
- 简单显示状态

Python 适合：

- 文件 IO
- 网络请求
- 数据库
- 复杂算法
- 系统 API
- 剪切板、热键、托盘

## 21. 推荐学习顺序

如果你是 PyQt/QML 新手，建议按这个顺序读代码：

1. `pyproject.toml`：看项目依赖和入口。
2. `src/app/main.py`：看应用如何启动。
3. `src/app/Main.qml`：看根 QML。
4. `src/app/launcher/LauncherWindow.qml`：看搜索框和插件承载。
5. `src/app/launcher/launcher_bridge.py`：看 QML 如何调用 Python。
6. `src/features/json_parser/`：学习最小完整插件。
7. `src/features/qr/`：学习 ViewModel + Service 分层。
8. `src/features/image_compress/`：学习插件如何读取输入和剪切板上下文。
9. `src/features/clipboard/`：学习后台插件、SQLite、剪切板监听。
10. `src/features/api_test/`：学习复杂窗口插件和更大的业务服务。
11. `docs/project-design.zh-CN.md`：理解当前架构边界、插件生命周期、平台层、存储、日志和并发约定。

每读一个插件，都回答这 6 个问题：

- 它的 `plugin.json` 声明了什么？
- 它什么时候加载 Runtime？
- 它的 `launchMode` 是什么？
- 它的 ViewModel 叫什么，QML 里怎么访问？
- 它有没有 Service？Service 负责什么？
- 它关闭时有没有资源需要释放？

## 22. 维护本文档的规则

为了让教程随着项目同步更新，后续改代码时请同时检查：

- 新增依赖：更新“技术栈”章节。
- 改启动流程：更新“从启动流程开始理解”章节。
- 新增插件：更新“推荐学习顺序”或增加插件案例。
- 改 Manifest 字段：更新“插件清单”章节。
- 改 launchMode/activation 行为：更新插件生命周期相关章节。
- 新增通用 UI 组件：更新“主题与通用 UI 组件”章节。
- 新增测试脚本：更新“如何运行和验证”章节。

本项目的学习目标不是背 API，而是掌握这条主线：

```text
Qt 事件循环
  -> QML 界面
  -> Python QObject
  -> Signal / Slot / Property
  -> 插件 Manifest
  -> Runtime / Session
  -> ViewModel / Service
  -> 测试和验证
```

只要这条线打通，你就能读懂当前项目，也能自信地新增自己的桌面工具插件。

# 类 uTools 改造实现说明（第一阶段）

本文档记录当前已经落地的第一阶段改造。它面向 Python 新手，重点解释核心代码为什么这么拆，以及启动器从“搜索”到“打开插件”的调用链。

更完整的目标架构见：

- [类 uTools 架构设计文档](./utools-like-architecture.zh-CN.md)
- [插件开发文档](./plugin-development.zh-CN.md)

## 1. 本阶段目标

本阶段已经切换为“全新设计主链路”，不再兼容旧版插件注册表和旧版快速启动数据库。现有功能页面和 ViewModel 会继续复用，但它们现在由新的 Manifest/Runtime/Session 架构调度。

本阶段先建立新的核心边界：

- `commands`：负责“什么东西能被搜索和启动”。
- `plugins`：负责“插件什么时候创建、什么时候释放”。
- `launcher`：负责“QML 输入框如何调用 Python”。

同时解决一个关键问题：

> 应用启动时不再创建所有插件 ViewModel，而是在用户真正启动插件时才创建。

这就是懒加载的第一步。

## 2. 新增核心模块

### `app.commands`

路径：

```text
src/app/commands/
  command_index_db.py
  context.py
  command_service.py
  dynamic_command_registry.py
```

#### 搜索结果模型

当前搜索结果直接使用 Python `dict` 传给 QML。这是有意的：Qt/QML 对 Python 字典和 `QVariantMap` 支持更直接，当前阶段不再保留额外的 `CommandItem` 包装类。

一条搜索结果大致长这样：

```python
{
    "id": "json-parser",
    "name": "JSON 解析",
    "source": "plugin",
    "mode": "inline_view",
    "pluginId": "json-parser",
    "commandId": "json-parser.open",
}
```

这样可以减少一层目前用不上的类型转换。后续如果需要更强约束，可以再引入类型模型，但不要为了“看起来完整”提前增加未使用抽象。

#### `CommandIndexDb`

文件：`src/app/commands/command_index_db.py`

新的命令索引数据库，不再兼容旧 `quick_start.db`。

它负责：

- 命令使用次数。
- 最近使用时间。
- Windows 应用快捷方式缓存。
- 系统应用扫描。

默认数据库文件是：

```text
data/command_index.db
```

#### `CommandService`

文件：`src/app/commands/command_service.py`

`CommandService` 是统一搜索和启动外部项目的入口。

它现在做这些事：

- 搜索插件 Manifest 声明的命令。
- 搜索系统工具。
- 搜索 Windows 应用快捷方式。
- 首次搜索时，如果没有系统应用缓存，则触发应用扫描。
- 启动系统工具或系统应用。
- 记录插件、系统工具、系统应用的使用次数。

注意：`CommandService` 不负责创建插件 ViewModel，也不负责加载 QML。

上下文推荐和前缀匹配也遵守这个边界：插件在 Manifest 中声明 `keywords`、`prefixes`、`matchers`，`CommandService` 只做通用排序，不在核心层硬编码某个插件的专属规则。

当前实现中，`src/app/commands/context.py` 负责生成 `LauncherContext`，包括输入框前缀、前缀后的正文、输入内容类型，以及最新剪切板内容类型。`CommandService` 只读取这些通用上下文和插件声明来计算排序分。

### `app.plugins`

路径：

```text
src/app/plugins/
  manifest.py
  manifest_loader.py
  runtime.py
  plugin_manager.py
  session_manager.py
```

#### `manifest.py`

这个文件定义插件清单模型：

- `PluginManifest`
- `CommandContribution`
- `LaunchMode`

现在每个插件都通过 `PluginManifest` 描述。旧的 `FeaturePlugin` 注册链路和 `src/app/plugin` 单数包已经移除。

自带插件不再集中写在 Python 列表里，而是和用户插件一样放在插件包目录中：

```text
src/features/json_parser/plugin.json
src/features/system/about.plugin.json
```

`src/app/plugins/builtin.py` 已移除，核心层不再知道具体有哪些自带插件。

#### `manifest_loader.py`

文件：`src/app/plugins/manifest_loader.py`

这个文件负责插件包发现：

- 默认先扫描 `src/features/*/plugin.json` 和 `src/features/*/*.plugin.json`。
- 再扫描项目根目录的 `plugins/*/plugin.json`。
- 支持通过 `PY_DESKTOP_TOOLS_PLUGIN_DIR` 指定一个或多个插件目录。
- 把 JSON Manifest 转成 `PluginManifest`。
- 自带插件和用户插件的相对 `qmlPage` 和图标路径都会转换成 `file:///...` 绝对 URL，QML Loader 可以直接加载。

插件的 Runtime 可以写成 `runtime:create_runtime`。如果插件目录下有 `runtime.py`，`PluginManager` 会从该插件包目录加载它，不要求安装为 Python 包。

#### `runtime.py`

文件：`src/app/plugins/runtime.py`

这里定义插件运行时协议：

- `PluginContext`
- `PluginAction`
- `PluginRuntime`
- `PluginSession`
- `SimpleQmlRuntime`

当前大部分自带插件都使用 `SimpleQmlRuntime` 包装已有 ViewModel 和 QML 页面。

#### `PluginManager`

文件：`src/app/plugins/plugin_manager.py`

`PluginManager` 负责插件层面的管理。

当前它做的是：

- 启动时只持有 `PluginManifest`。
- 用户启动插件时，按 `entrypoint` 动态 import Runtime。
- Runtime 创建 Session。
- 插件关闭时调用 Runtime 的退出逻辑并释放引用。

关键点是：Runtime import 不发生在应用启动阶段，而发生在插件命令被选中之后。

#### `PluginSessionManager`

文件：`src/app/plugins/session_manager.py`

`PluginSessionManager` 管理插件会话生命周期。

当前第一阶段，一个 session 主要等价于：

- 一个懒创建的 ViewModel。
- 一个正在使用它的 QML 页面或窗口。

打开插件时：

```python
session = session_mgr.open_plugin(plugin_id)
```

它会：

1. 找到插件 Manifest。
2. 通过 PluginManager 懒加载 Runtime。
3. Runtime 创建 PluginSession。
4. Session 创建 ViewModel。
5. 把 ViewModel 临时注入 QML context。

关闭插件时：

```python
session_mgr.close_plugin(plugin_id)
```

它会：

1. 从 QML context 移除对应 ViewModel。
2. 从内部缓存移除 ViewModel。
3. 对 QObject 调用 `deleteLater()`。

这就是当前阶段“卸载插件”的实际含义。

### `app.launcher`

路径：

```text
src/app/launcher/
  launcher_bridge.py
```

#### `LauncherBridge`

`LauncherBridge` 是暴露给 QML 的桥。

它是 QML 和 Python 后端之间的唯一启动器桥接对象。

QML 里可以写：

```qml
launcherBridge.performSearch(text)
launcherBridge.launchItem(id, source)
launcherBridge.closePlugin(pluginId)
```

当前只暴露 `launcherBridge` 一个名字，避免新旧桥接概念混用。

## 3. 主入口变化

文件：`src/app/main.py`

旧启动流程曾经是：

```python
for p in registry.all():
    meta = p.meta()
    vm = p.create_view_model()
    ctx.setContextProperty(meta.context_property, vm)
```

这意味着应用一启动，所有插件 ViewModel 都被创建了。

现在改成：

```python
command_index = CommandIndexDb()
dynamic_commands = DynamicCommandRegistry()
manifests = load_all_plugin_manifests()
plugin_manager = PluginManager(manifests)
plugin_context = PluginContext(
    command_index=command_index,
    dynamic_commands=dynamic_commands,
)
background_mgr = BackgroundManager(manifests, plugin_manager, plugin_context)
session_mgr = PluginSessionManager(ctx, plugin_manager, plugin_context)
command_service = CommandService(
    manifests,
    command_index,
    dynamic_commands,
)
bridge = LauncherBridge(command_service, plugin_context.services)

ctx.setContextProperty("launcherBridge", bridge)
background_mgr.start_all()
```

启动时只创建：

- 新命令索引数据库。
- Manifest 驱动的插件管理器。
- 会话管理器。
- 命令搜索服务。
- QML 桥。

不会创建所有插件 ViewModel。

## 4. 插件启动调用链

以用户打开“JSON 解析”为例。

### 第一步：QML 点击搜索结果

文件：`src/app/launcher/LauncherWindow.qml`

```qml
launcherBridge.launchItem(id, src)
```

插件也和系统应用一样，统一通过 `launchItem` 启动。

### 第二步：LauncherBridge 发出插件启动信号

文件：`src/app/launcher/launcher_bridge.py`

```python
def launchItem(self, item_id: str, source: str) -> None:
    if source == "plugin":
        self.launchPlugin(item_id)
        return
```

然后：

```python
def launchPlugin(self, plugin_id: str) -> None:
    self._command_service.record_plugin_launch(plugin_id)
    self.pluginLaunched.emit(plugin_id)
```

这里记录使用次数，并发出 `pluginLaunched` 信号。

### 第三步：main.py 接收信号

文件：`src/app/main.py`

```python
bridge.pluginLaunched.connect(on_plugin_launched)
```

当插件启动时：

```python
session = session_mgr.open_plugin(plugin_id)
```

这一步才真正 import 插件 Runtime，并创建 ViewModel。

### 第四步：根据插件模式打开 UI

如果插件启动模式是 `inline_view`：

```python
launcher_window.enterMixedMode(plugin_id)
```

输入框下方加载插件 QML。

如果插件启动模式是 `window`：

```python
_open_independent_window(plugin_id, session)
```

打开独立窗口。

## 5. 插件关闭调用链

### 内嵌插件关闭

用户按 Escape 或退出 mixed mode 时：

```qml
launcherBridge.closePlugin(closingPluginId)
```

然后 Python 收到：

```python
bridge.pluginClosed.connect(session_mgr.close_plugin)
```

最终释放 ViewModel。

### 独立窗口关闭

独立窗口关闭时：

```python
def _on_closed():
    _plugin_windows.pop(plugin_id, None)
    session_mgr.close_plugin(plugin_id)
```

窗口引用和 ViewModel 都会清理。

## 6. 当前阶段的“懒加载”程度

已经实现：

- 启动时不再创建所有 ViewModel。
- 启动时不再使用旧 `PluginRegistry`。
- 启动时不再使用旧 `QuickStartDb`。
- 旧 `src/app/plugin` 单数包、旧 `features/*/plugin.py` 入口和旧 AppLauncher QML/ViewModel 已移除。
- 插件 Manifest 成为主注册来源。
- Runtime 按 entrypoint 懒加载。
- 插件启动时才创建 ViewModel。
- 内嵌插件退出时释放 ViewModel。
- 独立窗口关闭时释放 ViewModel。
- 新命令索引写入 `data/command_index.db`。
- 剪切板插件已拆成后台监听服务和懒加载嵌入 UI。
- 剪切板插件已迁移到 `inline_view` 模式，历史、详情和设置嵌入在 Launcher 输入框下方。
- 插件动态命令注册表已完成；剪切板当前只保留一个主入口，避免搜索结果里出现多个剪切板入口。

还没有完全实现：

- 更完整的智能匹配规则。

说明：协议类型已经建立，但当前大部分插件仍使用 `SimpleQmlRuntime`。后续可以逐个插件升级成更细的自定义 Runtime。

## 7. 剪切板后台插件实现

剪切板插件是当前第一个真正的后台插件样板。

它的 Manifest 在 `src/features/clipboard/plugin.json` 中声明：

```json
{
  "id": "clipboard",
  "activation": "background",
  "entrypoint": "runtime:create_runtime"
}
```

这表示应用启动时会加载它的 Runtime，并执行后台启动逻辑。

### 后台启动链路

应用启动时：

```python
manifests = load_all_plugin_manifests()
background_mgr = BackgroundManager(manifests, plugin_manager, plugin_context)
background_mgr.start_all()
```

`BackgroundManager` 会找到所有 `activation="background"` 的插件，然后：

1. 通过 `PluginManager.ensure_runtime(plugin_id)` 懒加载 Runtime。
2. 如果 Runtime 有 `on_background_start(ctx)` 方法，则调用它。
3. Runtime 可以把后台服务放进 `PluginContext.services`。

剪切板 Runtime 会注册：

```python
ctx.services["clipboard.background"] = ClipboardBackgroundService(...)
```

### 服务拆分

文件：`src/features/clipboard/service.py`

现在拆成三层：

- `ClipboardHistoryStore`：只负责 SQLite 历史记录。
- `ClipboardMonitor`：只负责监听系统剪贴板。
- `ClipboardBackgroundService`：组合 Store 和 Monitor，对外提供后台服务。

这样 UI 不再拥有剪贴板监听器。

### UI 懒加载

用户打开剪切板插件时：

```python
ClipboardRuntime.on_enter(...)
```

它会复用后台服务：

```python
service = ctx.services["clipboard.background"]
view_model = ClipboardViewModel(service)
```

剪切板现在复用 `ClipboardWindowViewModel` 承载嵌入式 UI。打开剪切板命令时，Runtime 返回一个自定义的 `ClipboardInlineSession`：

```python
ClipboardInlineSession(
    manifest=action.manifest,
    view_model=ClipboardWindowViewModel(service, initial_query=action.input_text),
)
```

嵌入页面是：

```text
src/features/clipboard/ClipboardWindowPage.qml
```

它把历史列表、详情预览、重新复制、置顶、删除、清空、记录类型开关、过滤规则、文本长度上限和快捷键配置放在 Launcher 输入框下方。页面内部不再有独立搜索框，Launcher 输入框就是剪切板过滤框。

输入转发链路：

```text
Launcher 输入框变化
  -> LauncherBridge.setPluginInput(plugin_id, text)
  -> PluginSessionManager.update_plugin_input(plugin_id, text)
  -> ClipboardInlineSession.on_input_changed(text)
  -> ClipboardWindowViewModel.refreshHistory(text)
```

键盘选择链路：

```text
Launcher 输入框 Up/Down/Enter
  -> Loader 当前插件页 moveSelection()/activateSelection()
  -> 剪切板页移动选中项 / 复制当前选中项
```

搜索结果中剪切板只保留 Manifest 主入口 `clipboard.open`。后台 Runtime 不再注册 `剪切板设置` 或 `复制最新剪切板内容` 这类额外剪切板动态命令，避免默认列表中出现多个剪切板入口。

它不负责启动系统剪贴板监听。

### 关闭行为

关闭剪切板 UI 时：

- 只关闭当前 inline session 和 `ClipboardWindowViewModel`。
- 后台 `ClipboardBackgroundService` 继续运行。
- 应用退出时，`BackgroundManager.stop_all()` 才关闭后台监听和数据库连接。

这就是类 uTools 里“后台能力常驻，UI 按需打开”的核心模式。

## 8. 通用列表插件模板

当前 Launcher 已支持 `launch_mode="list"`。

列表插件的交互链路：

1. 用户在全局搜索中启动一个 `list` 命令。
2. `main.py` 创建对应 `PluginSession`。
3. 如果 `session.launch_mode == "list"`，则调用：

```python
bridge.setPluginListItems(session.list_model())
launcher_window.enterPluginMode(plugin_id, "list")
```

4. QML 中的 `pluginListView` 使用统一模板渲染：

```qml
model: launcherBridge.pluginListItems
```

5. 输入框内容变化时：

```qml
launcherBridge.setPluginInput(mixedPluginId, text)
```

Python 侧会调用：

```python
session.on_input_changed(text)
```

然后刷新 `pluginListItems`。

6. 用户按回车或点击列表项时：

```qml
launcherBridge.activatePluginListItem(pluginId, itemId)
```

Python 侧会调用：

```python
session.on_list_item_selected(item_id)
```

剪切板曾经作为第一个 `list` 模式样板，后来迁移为 `inline_view`：它仍然复用 Launcher 输入框过滤，但需要自定义区域展示历史、详情和设置。后续更适合用 `list` 模式的插件是“软件快速启动”“最近文件”“轻量历史记录”等。

## 9. 插件动态命令

动态命令用于解决这个需求：

> 插件在运行时根据自己的状态，向启动器插入额外命令。

例如未来下载插件可以在后台任务存在时插入“打开下载任务”或“暂停所有下载”。这些命令不是 Manifest 里的主入口，而是 Runtime 根据运行状态动态注册的。

### 动态命令注册表

文件：`src/app/commands/dynamic_command_registry.py`

核心类型：

```python
@dataclass(frozen=True)
class DynamicCommand:
    plugin_id: str
    command_id: str
    title: str
    subtitle: str = ""
    icon: str = ""
    keywords: list[str] = field(default_factory=list)
    launch_mode: LaunchMode = "none"
    payload: dict = field(default_factory=dict)
```

`DynamicCommandRegistry` 是一个进程内注册表，负责保存当前运行期的动态命令。

### 注册链路

`main.py` 创建注册表：

```python
dynamic_commands = DynamicCommandRegistry()
plugin_context = PluginContext(
    command_index=command_index,
    dynamic_commands=dynamic_commands,
)
```

后台插件启动时可以注册命令：

```python
ctx.dynamic_commands.register(
    DynamicCommand(
        plugin_id="download",
        command_id="download.pause_all",
        title="暂停所有下载",
        launch_mode="none",
    )
)
```

注意：剪切板插件当前不注册动态命令，因为产品要求搜索结果里只有一个剪切板入口。

### 搜索链路

`CommandService.search()` 会合并这些来源：

- Manifest 固定插件命令。
- DynamicCommandRegistry 中的动态命令。
- 系统工具。
- Windows 应用。

搜索前，`LauncherBridge` 会读取最新剪切板记录并构造 `LauncherContext`。排序大致遵守：

```text
前缀命中 > 明确文字匹配 > 输入内容类型推荐 > 剪切板内容类型推荐 > 使用频率 > Manifest order
```

为了避免剪切板推荐干扰明确搜索，输入框有明确文字时，剪切板 matcher 只会作用在已经被文字或前缀命中的命令上。例如剪切板是图片时，空输入会优先推荐图片压缩；但输入 `calc` 时，计算器仍然排在前面。

所以动态命令会自然出现在启动器搜索结果里，并且后续也可以通过 `prefixes`、`matchers` 接入同一套推荐机制。

### 启动链路

以前插件启动只传 `plugin_id`。

现在启动桥会传：

```python
plugin_id
command_id
input_text
payload
```

`input_text` 由 `CommandService` 统一判定：

- `inputSource == "command"`：用户输入的是插件前缀、缩写 alias、标题或关键词，用于选择插件，不作为业务内容传给插件，此时 `input_text == ""`。
- `inputSource == "content"`：用户输入本身被 matcher 识别为业务内容，例如 JSON、URL、图片文件路径，此时 `input_text` 是完整输入。
- `clearInputOnEnter` 是框架字段。只要启动插件前输入框有内容，进入插件模式后 Launcher 会静默清空输入框，避免把命令词继续留在外层输入框里。

文件：`src/app/launcher/launcher_bridge.py`

```python
pluginCommandLaunched = Signal(str, str, str, "QVariantMap")
```

`main.py` 收到后：

```python
session_mgr.open_plugin(
    plugin_id,
    command_id=command_id,
    input_text=input_text,
    payload=payload,
)
```

Runtime 可以根据 `action.command_id` 判断执行哪个命令。

`NoopPluginSession` 表示命令执行完没有 UI。`main.py` 会关闭 session 并隐藏 Launcher。

### 当前限制

当前动态命令是进程内注册表：

- 应用重启后由后台插件重新注册。
- 不做跨重启持久化。
- 不做第三方插件隔离。

这符合第一版目标，后续如有需要再把动态命令持久化到 `CommandIndexDb`。

## 10. 系统应用图标链路

Windows 应用图标由新命令索引模块负责。

相关文件：

```text
src/app/commands/command_index_db.py
```

流程：

1. `CommandService.search()` 首次发现系统应用缓存为空，或已有应用没有图标时，会触发扫描。
2. 扫描函数：

```python
scan_windows_shortcuts(command_index.get_icon_dir())
```

3. `scan_windows_shortcuts()` 会扫描开始菜单和桌面 `.lnk`。
4. 对每个 `.lnk`，优先解析目标 exe 并提取 exe 图标，失败时回退到 `.lnk` 自身图标。
5. 图标保存到：

```text
data/app_icons/
```

6. `CommandIndexDb.sync_apps()` 把 `icon_path` 写入 `data/command_index.db`。
7. QML 搜索结果中，如果 `icon_path` 存在，会使用：

```text
file:///.../data/app_icons/xxx.png
```

如果图标提取失败，才回退到：

```text
qta:mdi6.application-outline
```

注意：`data/app_icons/` 和 `data/*.db` 都是运行时缓存，已经在 `.gitignore` 中忽略。

## 11. 快速重启应用

应用现在有两个快速重启入口：

- 启动器搜索 `重启应用`、`restart`、`reload`。
- 系统托盘菜单点击 `重启应用`。

相关文件：

```text
src/app/app_relauncher.py
src/app/commands/command_service.py
src/app/launcher/launcher_bridge.py
src/app/tray/system_tray_manager.py
src/app/main.py
```

### 启动器入口

`CommandService` 中内置了一个系统命令：

```python
{
    "id": "restart-app",
    "name": "重启应用",
    "action": "__restart_app__",
}
```

`LauncherBridge.launchItem()` 发现这个特殊 action 后，不会走 `subprocess.Popen(action)`，而是发出：

```python
restartRequested = Signal()
```

`main.py` 收到后执行：

```python
restart_current_app()
qt_app.quit()
```

### 托盘入口

`SystemTrayManager` 增加了：

```python
restartRequested = Signal()
```

右键托盘菜单里有 `重启应用`，触发同一个 `restart_app()` 函数。

### 重新启动方式

`restart_current_app()` 在开发环境中使用：

```text
python -m app.main
```

并自动把仓库的 `src/` 加入新进程的 `PYTHONPATH`。这样无论当前是从 IDE、终端还是入口脚本启动，都能用同一个模块入口重启。

## 12. Launcher 尺寸规则

Launcher 的尺寸策略在：

```text
src/app/launcher/LauncherWindow.qml
src/app/launcher/PluginWindow.qml
```

当前规则：

- Launcher 输入框窗口宽度固定为 `800`。
- 普通搜索模式默认大小为 `800 x 600`。
- `inline_view` 插件模式保持 `800 x 600`。
- Launcher 输入框窗口位置也只在打开时由 Python 层按鼠标所在屏幕居中一次，QML 中不再持续绑定 `Screen.width` / `Screen.height`。
- 独立插件窗口默认大小为 `800 x 600`，可由插件 Manifest 的 `window.width` / `window.height` 覆盖。
- 独立插件窗口尺寸会作为 QML 初始属性传给 `PluginWindow.qml`，窗口显示后再校准一次，避免窗口先按默认 `800 x 600` 创建导致实际启动尺寸不稳定。这个延迟校准必须先检查 Qt 窗口对象是否仍然存活，避免用户快速关闭窗口或快速重启时访问已经销毁的 `QQuickWindow`。
- 独立插件窗口位置只在打开时由 Python 层居中一次，不在 QML 中绑定 `Screen.width` / `Screen.height`。持续绑定会在跨显示器拖动时反复重算位置，导致窗口闪烁和尺寸跳动。
- 独立插件窗口标题栏图标使用插件 Manifest 的 `icon`。
- 独立插件窗口的标题栏/任务栏图标由 Python 层读取 Manifest 后调用原生窗口 API 设置，不在 `PluginWindow.qml` 里写 `icon.source`。原因是当前 QtQuick `Window` 在本项目环境中没有可用的 `icon` 分组属性，写在 QML 会导致整个独立窗口组件创建失败，API 测试这类 `window` 插件会无法启动。
- `list` 插件模式宽度固定 `800`，高度由列表项数量决定。
- `list` 模式最多按 8 行计算高度，超过后列表内部滚动。
- Launcher 的 `y` 坐标按 `800 x 600` 的默认高度居中计算，不随 list 高度变化，避免输入框位置跳动。

这条规则的目的：

> 输入框在搜索、列表插件、内嵌插件之间切换时，宽度和顶部位置保持稳定。

## 13. 剪切板增强实现

剪切板插件现在不再是“只保存文本”的简单历史列表，而是第一个比较完整的后台插件样板。

相关文件：

```text
src/features/clipboard/service.py
src/features/clipboard/runtime.py
src/app/launcher/LauncherWindow.qml
src/app/hotkey/win_hotkey_manager.py
src/app/main.py
```

### 历史数据模型

剪切板历史表已经升级为通用条目：

```text
clipboard_history
  id
  item_type      text / image / files
  content        文本内容、图片路径或文件路径 JSON
  preview        列表展示用摘要
  metadata       JSON 元数据
  pinned         是否置顶
  created_at
```

这让同一个列表模板可以展示文本、图片和文件。

图片不会直接存进数据库，而是保存到：

```text
data/clipboard_assets/images/
```

数据库只记录图片文件路径、宽高等元数据。这个目录属于运行时缓存，已经加入 `.gitignore`。

前台 ViewModel 会把三类历史转换成适合 UI 展示的数据：

- 文本：标题使用文本摘要，详情使用完整文本。
- 文件：标题优先展示文件名，详情展示完整路径列表。
- 图片：标题展示尺寸，`imageUrl` 指向保存后的 PNG，用于列表缩略图和详情大图预览。

### 剪切板设置

新增设置表：

```text
clipboard_settings
  key
  value
```

当前支持：

- `capture_text`：是否记录文本。
- `capture_image`：是否记录图片。
- `capture_files`：是否记录文件。
- `max_text_chars`：文本最大长度，超过后不记录。
- `ignore_patterns`：过滤规则列表，支持关键词或正则。
- `hotkey`：剪切板历史快捷键，默认 `Alt+V`。

过滤规则在 `ClipboardHistoryStore.should_capture()` 中执行。监听器只负责读取系统剪贴板，是否记录交给 Store 判断。

### 图片和文件复制

剪切板后台服务现在提供：

```python
copy_item(item)
copy_item_by_id(item_id)
```

复制规则：

- `text`：调用 `QClipboard.setText()`。
- `image`：读取保存的 PNG 后调用 `QClipboard.setImage()`。
- `files`：构造 `QMimeData` 和 `QUrl.fromLocalFile()`，再调用 `QClipboard.setMimeData()`。

因此列表里选中任意类型，都可以重新写回系统剪贴板。

剪切板嵌入页支持：

- `Up/Down` 移动选中历史。
- `Enter` 复制当前选中项。
- 双击列表项复制当前项。
- 文件条目在列表中展示文件名。
- 图片条目在列表中展示缩略图，并在右侧详情区域展示大图预览。

### 置顶和删除

通用 `PluginSession` 协议保留了列表行内动作：

```python
def on_list_item_action(self, item_id: str, action_id: str) -> list[dict]:
    ...
```

`LauncherBridge` 对应新增：

```python
activatePluginListItemAction(plugin_id, item_id, action_id)
```

QML 的通用列表模板现在允许每一行携带：

```python
{
    "actions": [
        {"id": "pin", "label": "置顶", "icon": "qta:mdi6.pin-outline"},
        {"id": "delete", "label": "删除", "icon": "qta:mdi6.delete-outline"},
    ]
}
```

这条通道仍然用于未来的 `list` 插件。剪切板嵌入页不走 `on_list_item_action()`，而是由 `ClipboardWindowViewModel.togglePin()` 和 `ClipboardWindowViewModel.deleteItem()` 直接处理。置顶项排序在普通项之前。

### 剪切板入口与设置

剪切板搜索结果现在只保留一个入口：

- `剪切板历史`

启动该入口后，Launcher 进入 `inline_view` 插件模式。输入框里的文字会直接过滤剪切板历史；切换到页面内的“设置”页可以配置：

- 开关文本/图片/文件记录。
- 保存过滤规则。
- 保存文本长度上限。
- 保存剪切板快捷键。
- 清空历史。

设置表单仍在剪切板嵌入页里填写，不再依赖额外的“剪切板设置”动态命令。

### 剪切板快捷键

`WinHotkeyManager` 已从固定 `Alt+Space` 改造成可配置热键管理器。

当前注册两类全局热键：

- `Alt+Space`：打开主 Launcher。
- 剪切板配置里的 `hotkey`：直接打开剪切板历史，默认 `Alt+V`。
- Manifest 命令里的 `hotkey`：直接启动对应插件命令。若命令是 `window`，会直接打开独立窗口。

当 `clipboard_settings.hotkey` 改变时，后台 Store 会发出 `configChanged`，`main.py` 会重新注册剪切板热键。

注意：热键注册可能失败，例如快捷键无效或已经被其他应用占用。失败时会在控制台打印警告，但不会影响主应用继续运行。

## 14. 现有插件形态适配记录

这次重新按类 uTools 形态审查了已有插件。

当前结论：

- `clipboard`：已改为 `background + inline_view`。后台监听常驻，嵌入页集中承载历史、详情和设置，Launcher 输入框负责过滤历史；搜索结果只保留一个剪切板入口。
- `api-test`：保持 `window`。它是重型工作台，不适合放在 Launcher 输入框下方；Manifest 中配置默认窗口大小 `1000 x 600`。
- `json-parser`：主命令为 `inline_view`。直接粘贴 JSON 时会把完整 JSON 传入 ViewModel；用 `json` / `jq` 前缀启动时只打开插件，不传业务输入。
- `download`：主命令已改为 `window`。下载属于长生命周期任务，后续应把任务状态进一步迁到后台 service。
- `packet-capture`：保持 `window`。已补列表裁剪和长 path 省略，后续如果接入真实代理，需要继续强化窗口布局。
- `image-compress`：保持 `inline_view`。优先读取输入框里的图片文件路径；没有输入时，会读取最新剪切板图片或图片文件记录。
- `qr-code`：保持 `inline_view`。直接粘贴 URL 或文本内容匹配时会传给生成页；用 `qr` / `qrcode` 前缀启动时只打开插件并清空外层输入框。
- `system-settings` / `about`：保持 `inline_view`。
- `app-launcher`：已改为 `list`。它不再依赖独立窗口里的搜索框，而是复用 Launcher 输入框进行过滤，选中后直接启动应用。

后续原则：

- 重型工作台、长生命周期任务、需要多区域管理的插件优先 `window`。
- 简短输入输出、低状态、低风险工具可以 `inline_view`。
- 输入即过滤、选择即执行的功能优先 `list`。
- 后台监听和任务执行不要绑在短生命周期 UI ViewModel 上。

## 15. API 测试插件第一轮修复记录

本轮对 `api-test` 做的是“让核心工作流可靠可用”，不是把所有规划能力一次性补齐。

已修复：

- 独立窗口启动链路已改为通过手动启动应用验证，`PluginWindow.qml` 应能加载 API 页面，并使用 `1000 x 600` 默认尺寸。
- `ApiTestService` 的数据库目录现在尊重 `PY_DESKTOP_TOOLS_DATA_DIR`，测试和运行数据可以隔离，不再固定写到仓库 `data/`。
- API 树现在以 `api_collection_nodes` 为唯一数据源。普通新增、重命名、删除、移动、展开收起、method/url 修改都按节点 `id` 单行更新；只有 OpenAPI 导入仍使用 `replace_collection_tree()`。
- 节点结构已统一为 `folder`、`endpoint`、`case`，层级约束固定为：`folder -> folder/endpoint`，`endpoint -> case`，`case` 无子节点。
- `ApiCollectionSidebar.qml` 不再生成业务 id，也不再在普通操作中本地改整棵树。它只负责基于当前行/当前上下文发出节点级意图，页面层调用 ViewModel/Service 完成落库后重新加载树。
- 树组件内部仍保留 `nodePath` 作为当前渲染快照里的定位结果，但持久化身份已经只使用数据库 `id`。`_nodeId`、`treePatched`、本地 `selected` 标记这一批旧过渡机制已经从主流程移除。
- 树 UI 使用扁平可见行模型渲染，每行携带 `nodeId`、`nodePath`、`depth`。右键菜单、重命名、移动等操作都从当前行身份出发，避免旧路径漂移导致错位。
- 接口树已补齐常用资源管理操作：根目录右键新建接口/分组/导入，分组新建子接口/子分组，接口新建场景，节点移动、上下排序、复制、重命名、删除、展开/收起、全部展开/全部收起。
- 树行不再展示选中高亮，只保留 hover 反馈；选中状态只作为内部上下文定位存在，不再承担视觉表达。
- 场景 `case` 已经是独立请求快照。打开场景时会按 `requestSnapshot` 创建场景 Tab；编辑后会把 method/url/body/auth/headers/cookies/params/env/pre/post/mock 等字段写回该场景节点。
- 顶部 method / URL 现在会显式同步到当前 Tab 数据。普通接口节点会继续回写接口节点本身；场景节点只更新当前场景快照，不会误改所属接口。
- `http_tabs` 现在只以 `node_id` 关联树节点，不再依赖 `node_path` 持久化定位。
- 环境配置已经从 `app_state.environments` JSON 改成结构化表：`api_environments`、`api_environment_variables`、`api_environment_headers`。
- `ApiTestService` 已加入 schema version 管理。当前策略是不兼容旧数据：`PRAGMA user_version` 不匹配时，直接重建 API 测试插件自己的表。
- API 测试的数据访问边界已经进一步收口：`ApiDatabase` 负责 schema，`CollectionRepository` 负责 `api_collection_nodes`，`EnvironmentRepository` 负责环境三张表，`TabRepository` 负责 `http_tabs` 和 `http_history`。`ApiTestService` 保留为业务编排层，避免 QML/ViewModel 直接关心 SQL。
- `ApiTestViewModel` 已开始按 facade 方式瘦身。`RequestEditorState` 负责 params、headers、cookies、body、auth、mock、前后置脚本等请求编辑状态；`TabsController` 负责打开接口/场景、切换当前 Tab、关闭 Tab、把编辑器状态持久化到普通 Tab 或场景快照；`EnvironmentState` 负责环境列表和当前环境；`DebugCaseState` 负责调试用例列表和选择；`ResponseState` 负责响应标题、Body、响应头、实际请求、cURL 和请求日志分组；`RequestSenderCoordinator` 负责请求发送、busy/requestId、请求历史和 loading 回调。QML 暂时仍只访问 `apiTestVm.xxx`，避免一次性改动页面绑定。
- 已新增通用 `TaskRunner`，位于 `src/app/qt/task_runner.py`。它用 `QThreadPool + QRunnable` 执行后台任务，并用 QObject Signal 把成功/失败/完成回调送回 Qt 主线程。API 测试的 HTTP/file/mock/WebSocket 请求、下载任务、图片压缩任务已经接入 `TaskRunner`。
- 顶部请求 Tab 栏必须保留左右滚动按钮。只依赖 Flickable 鼠标滚动在多 Tab 时不够直观，也不适合触控板/鼠标滚轮行为不一致的场景。
- 接口管理侧边栏的右键菜单、新增菜单、过滤菜单都会按窗口可视区域做定位夹紧；菜单第一次打开后会在下一帧用真实 `implicitHeight` 再定位一次，避免首次弹出时高度未计算完整导致被窗口边缘截断。“移动到分组”二级菜单会在右侧放不下时自动翻到左侧。
- 接口工作区顶部的请求 Tab 栏只负责展示、切换、关闭已打开接口，并支持横向滚动。不要再从 Tab 栏新建接口，也不要再提供“保存到接口树”的按钮；接口的新建入口只保留在左侧接口树。
- 树节点行、树搜索框、顶部 URL 输入框、Body/前后置操作等输入控件都有 hover / focus 反馈。以后新增 API 测试输入控件时，优先复用 `UiTextField` / `UiTextArea`，表格内输入则保持 `ApiKvRow` 的轻量 hover 样式。
- 请求参数区域的 `Params` / `Body` / `Headers` 等 Tab 栏支持横向滚动，不再用固定 Row 挤压布局。
- 通用 `UiComboBox` 已收敛到设计系统颜色、字体和 hover 样式，API 测试里的方法、认证、类型等下拉框不再各自显得突兀。
- 参数表格里的类型字段不再复用通用 `ComboBox`，改为 `ApiTypeSelector` 这种表格内紧凑选择器，避免在 KV 行里显得厚重。
- HTTP 请求支持 `{id}` 这类路径参数替换。路径参数会参与 URL 生成，并从 query 参数里移除。
- Basic Auth 现在会把 `username:password` 正确 base64 后写入 `Authorization: Basic ...`。
- 前置操作不再被误当成普通 query 参数；它只交给 `ScriptService.apply_pre_ops()` 处理，例如 `set`、`header`、`query`、`body.append`。
- Mock 模式已接实。打开页面里的 Mock 开关后，发送请求不走网络，会返回 body 区域里的 mock 响应，并照常执行断言和写入历史。
- Body 模式收敛为当前真正可发送的 `none`、`x-www-form-urlencoded`、`JSON`、`XML`、`Text`，暂时移除会误导用户的 `form-data`、`Binary`、`msgpack`。
- Body 模式会自动补默认 `Content-Type`，但如果用户已手动填写 `Content-Type`，不会覆盖。
- 普通接口 Tab 草稿仍落到 `http_tabs`，场景 Tab 则直接写回场景节点快照，两条链路已经拆开。
- 环境管理弹窗已经从占位 UI 改成可编辑状态：支持新增/删除环境、编辑名称和 Base URL、新增/删除/启停环境变量，并把当前选中的环境索引带回页面。
- 发送请求时会根据当前环境读取启用的环境变量，参与 `{{var}}` 替换；响应提取变量也按环境名称存储，避免不同环境互相污染。
- 响应面板分为 `Body`、`Headers`、`Request`、`cURL`、`日志`。这些内容都由 Python 服务层通过 `details` 返回给 QML，页面只负责展示，不再拼请求细节。
- 响应结果不再存在 `ApiResponsePanel.qml` 的内部临时状态里，统一进入 Python `ResponseState`。`ApiResponsePanel` 只绑定 `apiTestVm.responseTitle/responseBody/responseHeaders/responseRequest/responseCurl/responseLog/responseLogs` 展示。后续做历史恢复、复制响应、导出响应时应继续从 `ResponseState` 或其演进对象取数据，不要把业务状态重新放回 QML 组件。
- `ApiTestViewModel` 已删除单一 `_dataChanged`，改用 `tabsChanged`、`editorChanged`、`responseChanged`、`environmentsChanged`、`collectionDataChanged`、`debugCasesChanged`、`wsTimelineChanged`、`apiHistoryChanged` 等按区域划分的 notify signal。新增属性时要选择最小合理的 notify，不要复用一个全局信号。
- HTTP 历史已在设置页展示最近请求。`TabRepository.list_history()` 从 `http_history` 按创建时间倒序读取，QML 点击历史项会恢复 method/url 到当前编辑区并保存当前 Tab 草稿。当前历史表只保存 method、url、状态、标题和响应正文，所以还不能完整恢复 headers/body/env；后续如要完整恢复，需要给历史记录补请求快照字段。
- `cURL` Tab 展示时允许为了可读性做换行排版，但服务层返回的 `curlText` 仍保持可复制的真实命令语义。后续如果要加复制按钮，应复制原始 `curlText`，不要复制 UI 排版后的文本。
- `日志` Tab 使用 `HttpRequestService._build_request_log()` 生成的 `requestLogText`，记录输入 URL、环境 Base URL、变量解析后的请求草稿、PreparedRequest、请求头、Body、cURL、响应状态、响应头、耗时和异常。页面会把多次请求按时间分组展示，但每组内容仍来自服务层。后续如果要补代理、证书、重定向、TLS、DNS 等排查信息，也应该继续扩展这个方法，不要在 QML 里临时拼。
- Mock / WebSocket 占位路径不会发起 HTTP 请求，但也会调用 `build_request_details()` 返回请求详情和日志。相对 URL 不能让日志生成失败；`HttpRequestService` 会在 `requests.PreparedRequest` 无法构造时回退到草稿日志。
- 发送按钮的 loading 不能只在 QML 里设置布尔值，因为同步请求会阻塞 UI 事件循环，loading 可能根本来不及绘制。当前发送链路已由 `RequestSenderCoordinator` 统一管理 HTTP busy、requestId 和 `TaskRunner` 后台任务，再通过 `apiSendingChanged`、`apiResponseReady`、`apiHistoryUpdated` 通知 ViewModel/QML。WebSocket 的连接、发送、接收、断开也由这个 coordinator 进入 `TaskRunner`，但不复用 HTTP loading，避免普通请求按钮和 WebSocket 操作互相影响。
- `WebSocketSessionService` 内部的连接字典已加 `RLock` 保护。后台任务可以并发触发连接、发送、接收、断开，但连接对象的增删读取必须通过 service 收口；不要在 ViewModel 或 QML 中直接缓存 websocket 对象。
- WebSocket 当前 Tab 状态由 `RequestSenderCoordinator` 回调到 `ApiTestViewModel` 的 `wsStatus/wsStatusText`，QML 顶部 WebSocket 操作条和设置页时间线只展示这份状态。后续做自动接收时，也应继续更新这个状态，不要在 QML 内部私自推断连接状态。
- 请求 / 响应面板的上下拖动用父容器坐标和像素高度计算，避免在拖动过程中用分隔条自身局部 `mouseY` 导致抖动。
- `ApiTestViewModel.dispose()` 不再盲目断开自己的 Signal。PySide6 在没有连接时调用 `disconnect()` 会打印 RuntimeWarning；当前只标记 disposed 并关闭 service，避免窗口关闭时产生无意义控制台噪音。
- 下载插件不再用裸 `threading.Thread` 直接回调 ViewModel；任务和进度更新都经由 `TaskRunner` 回到 Qt 主线程。单任务取消已接入：服务层维护取消标记，下载循环发现取消后会删除未完成文件，并把状态改成“已取消”。
- 图片压缩插件不再在 ViewModel Slot 里同步压缩图片；压缩任务经由 `TaskRunner` 后台执行，完成后再发 `imageCompressed`。
- 旧 `tools/feature_smoke.py` 已移除。后续验证以 `uv run python -m compileall src`、应用手动启动和重点交互回归为主。

仍属于后续规划：

- GraphQL 参数已有后端签名占位，但当前页面没有完整交互，不视为完成。
- `multipart/form-data`、二进制 body、msgpack body 需要单独设计请求体编辑器和文件选择，不应只在标签上暴露。
- HTTP 历史目前支持最近请求列表和 method/url 恢复；完整恢复 headers/body/env 还需要扩展历史表结构。
- WebSocket 已有连接、发送、接收、断开、当前 Tab 状态和 timeline 的后台任务链路，但还缺少自动接收和更完整的错误恢复。

## 16. 后续继续改造时的规则

后续开发请遵守：

- 新插件不要在 `main.py` 里直接创建 ViewModel。
- 新插件必须先有轻量 Manifest，再有 Runtime。
- 搜索项当前保持 dict 形态，字段由 `CommandService` 统一产出。
- 插件 UI 创建的对象要在 session 关闭时释放。
- 后台服务不要依赖 UI ViewModel。
- QML 统一调用 `launcherBridge`，不要再引入旧名 `pluginRegistry`。

## 17. Python 新手阅读建议

建议按这个顺序看代码：

1. `src/app/main.py`：看应用如何启动，以及各个管理器如何连接。
2. `src/app/plugins/manifest_loader.py`：看自带插件和用户插件如何被统一发现。
3. `src/features/*/plugin.json`：看自带插件如何声明命令、前缀和推荐规则。
4. `src/app/launcher/launcher_bridge.py`：看 QML 如何调用 Python。
5. `src/app/commands/command_service.py`：看搜索和系统项目启动。
6. `src/app/commands/dynamic_command_registry.py`：看动态命令如何保存。
7. `src/app/plugins/plugin_manager.py`：看 Runtime 如何被懒加载。
8. `src/app/plugins/session_manager.py`：看插件关闭时如何释放资源。
9. `src/app/plugins/background_manager.py`：看后台插件如何启动和停止。
10. `src/features/clipboard/runtime.py`：看后台插件如何常驻，并在需要时打开窗口 UI。
11. `src/features/clipboard/view_model.py`：看剪切板前台 ViewModel 如何复用后台服务，并响应外层输入过滤。
12. `src/app/launcher/LauncherWindow.qml`：看输入框如何调用桥接对象和渲染通用列表模板。

如果把它想成一句话：

> QML 负责用户操作，LauncherBridge 负责转发，CommandService 负责搜索，SessionManager 负责插件生命周期。

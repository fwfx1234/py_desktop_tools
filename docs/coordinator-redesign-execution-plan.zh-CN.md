# Coordinator 去中心化重构执行文档

本文由 5.5 模型负责架构设计，面向 5.4 执行模型落地。执行时不要重新发散架构方向，按本文分阶段、小步提交式改造。

## 1. 背景判断

当前代码中的 `coordinator` 不是同一种角色：

- `LauncherRuntimeCoordinator` 是应用运行期用例编排，已经同时处理启动器窗口、插件启动、Session、Surface、热键、剪贴板热键刷新和重启。
- `PluginSurfaceCoordinator` 是 QML Surface 管理器，负责 inline/list/window 三种承载方式、独立插件窗口、窗口保留和原生激活。
- `HotkeyCoordinator` 是全局热键注册服务，命名可改，但职责相对清楚。
- `TrayCoordinator` 只是 `SystemTrayManager` 的薄封装，价值很低。

因此本次重构目标不是把文件名里的 `coordinator` 换掉，而是把不同层级的职责拆回清晰边界。

## 2. 设计目标

- 启动路径读起来像应用生命周期，而不是一个总控脚本。
- 插件打开链路只有一个应用层入口：请求 -> Session -> Surface。
- QML Surface 只负责显示和销毁 UI，不判断 Session 是否复用。
- 热键和托盘是应用服务，不再挂在“运行协调器”概念下。
- 文件命名表达领域职责，避免继续新增泛化的 `*_coordinator.py`。
- 不新增 GUI 测试文件；涉及 UI 行为的验证通过直接启动应用和受影响插件完成。

## 3. 非目标

- 不重写插件系统。
- 不改变 manifest 协议。
- 不改变现有插件目录结构。
- 不引入 IoC 容器、事件总线或大型框架。
- 不在本次强行支持多实例插件；但新边界不能阻碍后续扩展。
- 不新增测试文件验证 GUI。只允许必要的语法检查和手动 GUI 回归。

## 4. 推荐最终模块

目标结构如下：

```text
src/app/
  app_runtime.py
    ApplicationRuntime

  app_bootstrap.py
    ApplicationBootstrapper

  app_context.py
    ApplicationContext

  application_controller.py
    ApplicationController

  launcher/
    launcher_window.py
      LauncherWindowController
    launcher_bridge.py

  plugins/
    session_manager.py
      PluginSessionManager
    launch_request.py
      PluginLaunchRequest
    host.py
      PluginHostService
      PluginWindowHandle

  hotkeys/
    lifecycle.py
      HotkeyLifecycle
      ClipboardHotkeyProvider
    service.py
      HotkeyService

  tray/
    system_tray_manager.py
    service.py
      TrayService
```

按最新架构直接迁移到新模块名；旧文件名和旧入口直接删除。

## 5. 职责边界

### 5.1 ApplicationRuntime

只做三件事：

1. 创建 `ApplicationBootstrapper`。
2. 拿到 `ApplicationContext` 后调用 `start()`。
3. 进入 `QApplication.exec()`，退出后交给 `ApplicationContext.shutdown()` 清理。

不要把插件打开、热键注册、托盘信号连接、QML 窗口定位写回这里。

### 5.2 ApplicationBootstrapper

负责组装对象，不负责运行期业务：

- 创建 `QQmlApplicationEngine`。
- 注入 `app` 和 `launcherBridge`。
- 创建 `StorageManager`、平台服务、命令服务、插件管理器。
- 加载 `Main.qml`。
- 创建 `ApplicationController`、`PluginSessionManager`、`PluginHostService`、`HotkeyService`、`HotkeyLifecycle`、`TrayService`。
- 返回 `ApplicationContext`。

Bootstrapper 可以知道所有依赖，但不要承载“用户点击后做什么”的逻辑。

### 5.3 ApplicationContext

负责应用生命周期：

- `start()`：连接应用层信号、安装热键、显示托盘、启动后台插件、调度应用索引刷新。
- `shutdown()`：按顺序停止热键、销毁 Surface、关闭 Session、停止后台插件、关闭 Runtime、关闭命令服务和数据库。

`ApplicationContext` 只调用服务公开方法，不写具体插件打开流程。

### 5.4 ApplicationController

替代 `LauncherRuntimeCoordinator` 的应用层用例入口。

它负责：

- 连接 `LauncherBridge` 发出的用户意图信号。
- 处理启动器显示/隐藏。
- 处理插件启动请求。
- 处理插件挂起、强制关闭、detach 到窗口。
- 处理 list 模式输入、列表项选中和动作。
- 处理重启。
- 协调 `PluginSessionManager` 与 `PluginHostService`。

它不负责：

- 创建 QML 独立插件窗口的细节。
- 注册系统热键的细节。
- 托盘菜单实现。
- 插件 Runtime 加载细节。

推荐公开方法：

```python
class ApplicationController:
    def connect(self) -> None: ...
    def toggle_launcher(self) -> None: ...
    def hide_launcher(self) -> None: ...
    def open_plugin(self, plugin_id: str, command_id: str = "", input_text: str = "", payload: dict | None = None) -> None: ...
    def open_plugin_request(self, request: PluginLaunchRequest) -> None: ...
    def suspend_plugin(self, plugin_id: str, host: str) -> None: ...
    def force_close_plugin(self, plugin_id: str) -> None: ...
    def detach_plugin_to_window(self, plugin_id: str) -> None: ...
    def on_retention_expired(self, plugin_id: str, state: SessionState) -> None: ...
    def restart_app(self) -> None: ...
```

原 `LauncherRuntimeCoordinator` 中的启动器定位、macOS/Windows 激活逻辑，不应长期留在 `ApplicationController` 内。先迁到 `LauncherWindowController`，再由 `ApplicationController.toggle_launcher()` 调用。

### 5.5 LauncherWindowController

负责启动器主窗口行为：

- 判断窗口是否可用。
- 居中到当前焦点屏幕或鼠标屏幕。
- show/hide。
- 预热。
- macOS/Windows 原生激活。
- `enterPluginMode()`、`detachInlinePlugin()`、`retainInlineHost()` 这类 launcher host 调用可先保留代理方法，后续再细化。

从 `LauncherRuntimeCoordinator` 迁出的函数：

- `_center_window_once`
- `_set_window_screen`
- `_center_launcher_window`
- `_restore_launcher_window_state`
- `_show_launcher_window`
- `_log_launcher_window_state`
- `_activate_and_log_launcher_window`
- `_configure_launcher_window_for_macos`
- `_activate_launcher_window_native`
- `_launcher_prewarm_enabled`
- `prewarm_launcher_window`
- `hide_launcher`

### 5.6 PluginHostService

替代 `PluginSurfaceCoordinator`。

职责：

- 根据已经创建好的 `PluginSession` 显示 UI。
- 管理独立插件窗口。
- 通知 launcher 进入 inline/list 模式。
- 挂起 inline/list host。
- 销毁插件窗口。
- 在 Session 保留到期时销毁或通知 QML。

不允许：

- 判断 Session 是否可复用。
- 创建或卸载 Plugin Runtime。
- 修改 `PluginSessionManager` 内部状态。

推荐接口：

```python
class PluginHostService:
    def show(self, request: PluginLaunchRequest, session: PluginSession) -> bool: ...
    def suspend(self, plugin_id: str, host: PluginHost) -> None: ...
    def destroy(self, plugin_id: str) -> None: ...
    def destroy_all(self) -> None: ...
    def notify_retention_expired(self, plugin_id: str, state: SessionState) -> None: ...
```

`show()` 内部按 `session.launch_mode` 和 `request.preferred_host` 决定显示 inline/list/window，但它只能做 Surface 决策，不能做 Session 决策。

### 5.7 HotkeyService

替代 `HotkeyCoordinator`。

职责：

- 管理 launcher 热键、剪贴板热键和插件热键。
- 安装 Qt/native 事件过滤器。
- 注册、刷新、注销热键。
- 读取外部传入的热键文本，不直接读取存储。

剪贴板热键具体从哪里读取，由 `HotkeyLifecycle` 内的小型 `ClipboardHotkeyProvider` 负责。不要让 HotkeyService 依赖 `PluginContext`。

推荐接口：

```python
class HotkeyService:
    def install_filters(self) -> list[object]: ...
    def assign_window_id(self, hwnd: int) -> None: ...
    def register_all(self, manifests: list[PluginManifest], *, clipboard_hotkey: str) -> None: ...
    def refresh_clipboard_hotkey(self, hotkey: str) -> None: ...
    def unregister_all(self) -> None: ...
```

### 5.8 HotkeyLifecycle

负责热键生命周期编排：

- 安装 root/plugin 事件过滤器并保存到 `qt_app` property。
- 在 launcher window id 可用后注册热键。
- 连接剪贴板配置变化并刷新剪贴板热键。
- manifest 刷新后更新插件热键。

它可以依赖 `PluginContext` 读取剪贴板服务配置，但不处理插件打开、Session 或 Surface。

### 5.9 TrayService

替代 `TrayCoordinator`。

它可以直接包一层 `SystemTrayManager`，但命名要表达“托盘服务”而不是协调器。

如果执行模型发现 `TrayService` 仍只是三行转发，可以选择不新建类，直接让 `ApplicationBootstrapper` 创建 `SystemTrayManager` 并在 `ApplicationContext.start()` 连接信号。二者选一，不要保留 `TrayCoordinator`。

## 6. 插件打开链路

目标链路：

```text
QML / hotkey / tray
  -> ApplicationController.open_plugin_request(request)
  -> PluginSessionManager.open_request(request)
  -> PluginHostService.show(request, session)
  -> 若 launchMode == none，立即 PluginSessionManager.unload_plugin(plugin_id)
```

处理不可复用 Session：

```text
ApplicationController.open_plugin_request(request)
  -> 如果已有 session 且不能复用
  -> PluginHostService.notify_retention_expired(plugin_id, old_state)
  -> PluginSessionManager.unload_plugin(plugin_id)
  -> PluginSessionManager.open_request(request)
```

挂起链路：

```text
QML close/suspend
  -> ApplicationController.suspend_plugin(plugin_id, host)
  -> PluginHostService.suspend(plugin_id, host)
  -> PluginSessionManager.suspend_plugin(plugin_id, host)
```

保留到期链路：

```text
PluginSessionManager retention timer
  -> ApplicationController.on_retention_expired(plugin_id, state)
  -> PluginHostService.notify_retention_expired(plugin_id, state)
  -> PluginSessionManager.unload_plugin(plugin_id)
```

窗口 retained close 链路：

```text
PluginWindow.qml retainedCloseRequested
  -> PluginHostService on_retained_close callback
  -> ApplicationController.on_surface_retained_close(plugin_id, "window")
  -> PluginSessionManager.suspend_plugin(plugin_id, "window")
```

## 7. 文件迁移步骤

### 阶段 0：冻结行为基线

执行前记录当前脏工作区，不要还原用户改动。

推荐命令：

```bash
git status --short
uv run python -m compileall src
```

如果 `compileall` 已失败，先记录失败原因，不要把既有失败混进重构结果。

### 阶段 1：引入新命名但保持行为

目标是低风险迁移文件名和类名：

1. 新建 `src/app/application_controller.py`，把 `LauncherRuntimeCoordinator` 复制/迁移为 `ApplicationController`。
2. 新建 `src/app/plugins/host.py`，把 `PluginSurfaceCoordinator` 复制/迁移为 `PluginHostService`。
3. 新建 `src/app/hotkeys/service.py`，把 `HotkeyCoordinator` 迁移为 `HotkeyService`。
4. 新建 `src/app/tray/service.py`，把 `TrayCoordinator` 迁移为 `TrayService`，或直接删除薄封装改用 `SystemTrayManager`。
5. 更新 `app_bootstrap.py` 和 `app_context.py` 的 import 与字段名。
6. 删除旧 `*_coordinator.py` 文件。

### 阶段 2：拆出 LauncherWindowController

从 `ApplicationController` 中迁出启动器窗口细节：

1. 新建 `src/app/launcher/launcher_window.py`。
2. 将启动器窗口定位、显示、隐藏、预热、激活逻辑迁入 `LauncherWindowController`。
3. `ApplicationController.toggle_launcher()` 只保留业务判断和调用。
4. `ApplicationController.open_plugin_request()` 中不直接调用 launcher window 的底层方法，改用 `LauncherWindowController` 的代理方法。

验收标准：

- `ApplicationController` 中不再出现 `_center_launcher_window`、`_activate_launcher_window_native` 这类窗口底层方法。
- 平台原生 windowing import 只出现在 `LauncherWindowController` 或 `PluginHostService`。

### 阶段 3：收紧 PluginHostService

目标是让 host 只管 UI：

1. `PluginHostService.show()` 改为接收 `PluginLaunchRequest` 和 `PluginSession`。
2. 删除散乱参数 `plugin_id`、`input_text`、`payload` 组合。
3. `ApplicationController.open_plugin_request()` 负责所有 Session 决策。
4. list 模式的 `bridge.setPluginListItems()` 仍可留在 `PluginHostService`，因为这是显示 host 的一部分。
5. 强制关闭时先 `PluginHostService.destroy(plugin_id)`，再 `PluginSessionManager.unload_plugin(plugin_id)`。

验收标准：

- `PluginHostService` 不调用 `PluginSessionManager`。
- `PluginSessionManager` 不调用 `PluginHostService`。
- 二者只由 `ApplicationController` 串联。

### 阶段 4：热键生命周期独立

目标是让热键注册独立于应用控制器：

1. `ApplicationContext.start()` 调用 `HotkeyLifecycle.install()`，由它安装 filters 并把 filters 保存到 `qt_app` property。
2. `ApplicationController` 提供回调：`toggle_launcher`、`open_clipboard_history`、`open_plugin`。
3. `HotkeyService` 只接收这些回调，不读取插件上下文、不读取剪贴板配置。
4. 剪贴板配置变化时，由 `HotkeyLifecycle` 调用 `HotkeyService.refresh_clipboard_hotkey(hotkey)`。

验收标准：

- `HotkeyService` 只依赖 `PlatformServices`、`qt_app`、回调和 manifests。
- `_clipboard_hotkey_text()` 不在 HotkeyService 中。
- `ApplicationController` 不注册热键、不读取剪贴板热键配置。

### 阶段 5：托盘服务去薄封装

二选一：

- 方案 A：保留 `TrayService`，但用服务命名。
- 方案 B：删除包装层，`ApplicationContext` 直接持有 `SystemTrayManager`。

倾向方案 A，因为 `ApplicationContext` 字段更一致，未来托盘通知和菜单扩展有位置放。

验收标准：

- 不再存在 `tray_coordinator.py`。
- `ApplicationContext.start()` 中是 `tray_service.show()` 或 `tray_manager.show()`。

### 阶段 6：清理旧 coordinator 文件

当新模块已接管内部引用后：

1. 运行 `rg -n "coordinator|Coordinator" src docs AGENTS.md`。
2. 删除旧文件。
3. 更新文档中当前架构说明。

允许保留的例外：

- 历史文档中讨论旧设计的问题，可以出现 `coordinator`。
- 内部和文档都以新模块为准。

## 8. 验证方式

本项目 GUI 行为不要求新增测试文件。执行每个阶段后至少做：

```bash
uv run python -m compileall src
uv run app
```

启动应用后按影响范围直接打开相关插件和入口。

核心手动回归清单：

- `Alt+Space` 能显示和隐藏启动器。
- 启动器搜索结果正常出现。
- 打开 `json-parser`，输入内容，关闭后保留期内重新打开。
- 打开 `api-debugger` 独立窗口，关闭后保留期内重新打开。
- 打开 `clipboard` 历史窗口，确认剪贴板热键入口仍可用。
- 打开 `app-launcher` list 模式，输入过滤、选择项。
- 打开 `qr` 或 `image-compress` 这类普通 QML 插件，确认 context property 正常。
- 使用托盘菜单显示主窗口、重启、退出。

涉及热键阶段时额外验证：

- 默认 `Alt+Space`。
- 剪贴板热键。
- manifest 中声明的插件热键。

涉及 window host 阶段时额外验证：

- 窗口尺寸按 manifest 生效。
- `alwaysOnTop` 不回归。
- 关闭窗口不会立即销毁 Session。
- 保留到期后窗口和 context property 都被释放。

## 9. 执行注意事项

- 不要新增测试文件来覆盖 GUI 行为。
- 不要重写 unrelated feature 插件。
- 不要顺手改 UI 视觉。
- 不要把 Session 生命周期塞进 QML。
- 不要让 `LauncherBridge` 成为状态中心，它只是 QML 边界。
- 不要在后台线程访问 QML、`QApplication`、`QClipboard` 或托盘对象。
- 保持日志事件名稳定，除非文件迁移必须更新 logger name。
- 遇到现有脏文件，先阅读再改；不要还原用户修改。

## 10. 面向 5.4 执行模型的顺序

建议按以下顺序执行，不要一次性大改：

1. 新模块和类名迁移，保持方法体基本不变。
2. 更新 bootstrap/context 引用。
3. 运行 `compileall`，启动 app，验证主要插件。
4. 拆 `LauncherWindowController`。
5. 启动 app，重点验证启动器显示、隐藏、定位、热键。
6. 收紧 `PluginHostService.show(request, session)`。
7. 启动 app，重点验证 `json-parser`、`api-debugger`、`clipboard`、`app-launcher`。
8. 独立热键服务。
9. 启动 app，重点验证所有热键入口。
10. 处理托盘服务。
11. 启动 app，验证托盘显示、重启、退出。
12. 清理旧 coordinator 文件和文档引用。

每一步都要保持可运行。若某一步 GUI 回归失败，优先回到该阶段内修复，不要继续叠加后续阶段。

# Py Desktop Tools 项目设计文档

本文描述当前项目的长期设计。它不是阶段性改造计划，而是后续开发、重构和排查问题时优先参考的设计基线。

## 1. 产品定位

Py Desktop Tools 是一个基于 `PySide6 + QML` 的桌面工具箱，核心体验接近 uTools：

- 应用启动后常驻后台。
- 用户通过 `Alt+Space` 唤起启动器。
- 启动器搜索插件命令、系统工具、系统应用和插件动态命令。
- 插件按需加载，关闭可短暂保留会话状态。
- 少数后台插件可以随应用启动，例如剪贴板历史。

核心原则：

```text
启动器是应用本体，插件是被启动器调度的能力。
```

## 2. 启动流程

入口是 `src/app/main.py:main()`，主流程如下：

1. 初始化结构化日志。
2. 创建 `QApplication`，配置字体和 Qt Quick Controls 样式。
3. 创建 `ApplicationRuntime`。
4. `ApplicationRuntime.run()` 调用 `ApplicationBootstrapper.build()` 创建运行期上下文。
5. `ApplicationBootstrapper` 创建 QML engine、全局 ViewModel、平台服务、存储、命令索引、动态命令注册表。
6. 读取所有插件 Manifest，构造 `PluginManager`、`PluginSessionManager`、`BackgroundManager`、`CommandService`。
7. 注入全局 QML context：`app`、`launcherBridge`。
8. 加载 `Main.qml` 和启动器窗口。
9. `ApplicationContext.start()` 连接运行期信号、注册热键、显示托盘并启动后台插件。

`main.py` 保持薄入口；`app_runtime.py` 只保留高层运行流程，组装细节在 `app_bootstrap.py`，启动器与插件生命周期事件连接在 `application_controller.py`，热键注册和刷新在 `hotkeys/lifecycle.py`。

## 3. 目录职责

```text
src/
  app/
    main.py                  # 入口
    app_runtime.py           # 应用运行期高层流程
    app_bootstrap.py         # 应用上下文组装
    app_context.py           # 运行期对象集合与统一清理
    application_controller.py # 启动器和插件生命周期用例
    launcher/                # 启动器 QML、Bridge、搜索结果项
    commands/                # 搜索、排序、上下文匹配、系统/应用命令
    plugins/                 # Manifest、Runtime、Session、后台插件
    hotkeys/                 # 全局热键服务与生命周期
    platform/                # 平台抽象与 Windows/macOS/noop 实现
    services/                # 纯 Python 应用服务
    storage/                 # SQLite 和 dict store 封装
    logging/                 # 结构化日志
    concurrency/             # Python 后台任务
    tray/                    # 系统托盘
    ui/                      # 通用 QML 组件
    theme/                   # QML 主题令牌
  features/                  # 内置插件
```

依赖方向：

```text
QML -> ViewModel -> Service -> storage/platform/concurrency
Plugin Runtime -> PluginContext -> platform/storage/dynamic commands
LauncherBridge -> CommandService / ApplicationController
ApplicationController -> PluginSessionManager / PluginHostService
HotkeyLifecycle -> HotkeyService / ClipboardHotkeyProvider
```

业务 Service 默认不依赖 QML、QObject 或 Qt 控件。

## 4. 插件模型

每个插件由 `src/features/<plugin>/` 下的 Manifest 和 Runtime 组成：

```text
plugin.json
runtime.py
view_model.py
service.py
*.qml
components/
```

Manifest 只描述静态信息：

- `id`、`name`、`description`、`icon`
- `entrypoint`
- `qmlPage`
- `contextProperty`
- `activation`
- `commands`
- `window`

读取 Manifest 时禁止创建 ViewModel、加载 QML、启动线程、连接剪贴板或访问大型数据库。Runtime 只在命令启动或后台插件启动时加载。

## 5. Runtime 与 Session

核心类型在 `src/app/plugins/runtime.py`：

- `PluginContext`：插件可使用的上下文服务。
- `PluginAction`：一次命令启动的输入、payload、trace id。
- `PluginRuntime`：插件运行时协议，负责 `on_enter()` 和 `on_exit()`。
- `PluginSession`：一次插件交互的会话协议。
- `SimpleQmlRuntime`：普通 QML + ViewModel 插件的快捷 Runtime。

`PluginManager` 负责按 Manifest 懒加载 Runtime，并为插件目录创建合成包，使插件内部相对导入可用。

`PluginSessionManager` 负责会话状态：

- `active`：插件 UI 当前打开。
- `retained`：UI 关闭但 Session 暂时保留。
- `unloaded`：Session 已真正关闭，ViewModel 释放，Runtime 可按需关闭。

普通关闭优先 suspend，会话保留时间默认 5 分钟，可用 `PY_DESKTOP_PLUGIN_RETENTION_MS` 调试。再次启动同一插件时，如果输入和 payload 允许复用，会调用 `reactivate()`。

对 `inline_view` 而言，普通关闭后的链路是：Launcher 里的 QML host 先隐藏，Session / ViewModel / Runtime 进入 retained 状态并继续存活；5 分钟保留期内再次打开会优先复用原会话；只有保留到期、强制关闭或应用退出时，才会清空 context property、关闭 session，并由 `PluginManager` 释放 runtime。

后台插件的 Runtime 不会被普通 `close_runtime()` 关闭。

## 6. launchMode

插件命令支持以下启动模式：

| 模式 | 行为 |
|---|---|
| `none` | 执行动作后隐藏启动器，不显示 UI |
| `list` | 在启动器内显示插件提供的列表数据 |
| `inline_view` | 在启动器内嵌入插件 QML 页面 |
| `window` | 打开独立插件窗口 |

`width` / `height` 小于 `1.0` 时按屏幕比例计算，大于等于 `1` 时按像素计算。当前插件 Session 与 QML context 仍按 `pluginId` 管理，同一个插件暂时只支持单窗口实例；后续如需真正多实例，需要先引入独立 `sessionId`，并把 ViewModel 注入从全局 root context 调整为实例级 QML context。

## 7. 命令系统

`CommandService` 汇总四类结果：

- 插件 Manifest 声明的命令。
- 插件运行时注册的动态命令。
- 平台系统命令。
- 系统应用索引。

搜索时会经过：

1. `build_launcher_context()` 解析前缀和输入上下文。
2. `CommandRanker.score()` 计算文本匹配分。
3. `CommandContextMatcher` 应用前缀、matcher 和启动输入策略。
4. `CommandUsageService` 叠加使用频率。
5. 返回最多 50 条给 QML。

命令启动后由 `LauncherBridge` 发出插件启动、动态命令启动或外部应用启动信号。

## 8. 平台能力

平台层从 `src/app/platform/factory.py` 组装：

```text
platform/
  api.py
  factory.py
  models.py
  protocols.py
  services.py
  common/
  windows/
  macos/
  noop/
```

`PlatformServices` 聚合这些能力：

- 平台信息。
- 默认热键。
- 应用索引。
- 外部打开和系统动作。
- 剪贴板。
- 对话框。
- 屏幕信息。
- 插件存储。
- 动态命令。
- 权限。

插件通过 `ctx.platform` 或 `PlatformApi.for_plugin(plugin_id)` 使用能力，不直接 import Windows/macOS 实现。

系统动作必须经过允许列表，避免插件随意执行任意系统命令。

## 9. 存储

存储入口在 `src/app/storage/`：

- `StorageManager`：按数据目录创建数据库、dict store 和路径。
- `SQLiteDatabase`：封装 SQLite 连接、事务、WAL、外键和 row factory。
- `DatabaseDictStore`：用 SQLite 表模拟字典配置存储。

默认数据目录来自 `app.paths.user_data_dir()`，可用 `PY_DESKTOP_TOOLS_DATA_DIR` 覆盖。

推荐规则：

- 应用级数据库通过 `StorageManager.database(name)` 创建。
- 简单配置通过 `StorageManager.dict_store(namespace)` 创建。
- 插件私有数据优先走 `PlatformApi.storage`，保证路径和命名空间隔离。

## 10. 日志

日志系统位于 `src/app/logging/`，入口是 `init_logging()` 和 `get_logger()`。

设计约定：

- 文件日志使用 JSONL。
- 控制台日志使用简短文本。
- Qt/QML 消息接入 `qt.log`。
- 插件日志可按插件拆分。
- 敏感字段由 redaction 规则处理。
- 支持 trace id、session id、request id、task id。

常用环境变量：

| 变量 | 作用 |
|---|---|
| `PY_DESKTOP_TOOLS_LOG_DIR` | 覆盖日志目录 |
| `PY_DESKTOP_TOOLS_LOG_LEVEL` | 默认日志级别 |
| `PY_DESKTOP_TOOLS_LOG_CONSOLE` | 是否输出控制台 |
| `PY_DESKTOP_TOOLS_LOG_RETENTION_DAYS` | 日志保留天数 |

新增日志时优先记录事件名和结构化字段，不要只写自然语言字符串。

## 11. Qt 边界与并发

允许 import PySide6 的位置：

- `src/app/main.py`
- `src/app/app_runtime.py`
- `src/app/hotkeys/`
- `src/app/launcher/`
- `src/app/tray/`
- `src/app/plugins/host.py`
- `src/app/qta_icon_provider.py`
- `src/app/platform/` 中明确作为跨平台 SDK 实现的 Qt fallback，例如对话框、屏幕信息、全局热键
- `src/app/plugins/runtime.py`
- `src/app/plugins/session_manager.py`
- `src/features/*/view_model.py`

默认不应 import PySide6 的位置：

- `src/app/services/`
- `src/app/storage/`
- `src/app/commands/`
- `src/features/*/service.py`
- `src/features/*/*_state.py`
- `src/features/*/*_sender.py`，除非它明确是 ViewModel 边界。

耗时任务使用 `src/app/concurrency/task_runner.py` 的 Python runner。需要回到 UI 主线程时，由插件 ViewModel 自己负责，例如使用 ViewModel 私有 Signal 派发回调。

不要在后台线程直接操作 QML 对象、`QApplication`、`QClipboard`、文件对话框或托盘。

## 12. QML 与 UI 约定

QML 页面使用：

```qml
import "../../app/ui"
import "../../app/theme"
```

通用控件优先使用 `app/ui` 下的组件。颜色、间距、圆角等优先使用 `Theme.qml` 令牌。

QML 负责布局、绑定和轻量交互；业务逻辑、IO、网络、数据库和系统 API 放在 Python ViewModel 或 Service 中。

插件 ViewModel 只在插件 Session 活跃或保留期间注入到 QML context。关闭后 context property 会被清空。

## 13. 路径与打包

路径工具在 `src/app/paths.py`：

- `project_root()`：源码项目根目录。
- `resource_root()`：源码模式返回项目根；PyInstaller 模式返回 `_MEIPASS`。
- `user_data_dir()`：用户数据目录。
- `cache_dir()`：缓存目录。
- `plugin_dirs()`：外部插件目录，受 `PY_DESKTOP_TOOLS_PLUGIN_DIR` 控制。

PyInstaller spec 位于 `tools/suishou.spec`，会收集 `src/app`、`src/features` 和 `app` / `features` 子模块。

构建命令：

```bash
uv run build
```

macOS 热键依赖系统权限，打包、签名、公证和安装器仍需要在目标机器上单独验证。

## 14. 验证

常用验证命令：

```bash
uv run python -m compileall src
uv run app
```

```bash
uv run pytest
```

Windows / 历史 smoke 脚本仍可作为补充验证：

```powershell
scripts\smoke_import.ps1
scripts\smoke_plugin_manifests.ps1
scripts\smoke_storage.ps1
scripts\smoke_tests.ps1
```

本项目当前没有统一 lint/typecheck 命令；测试入口使用 `uv run pytest`。改动越靠近核心启动、插件生命周期、平台层、存储层或并发层，越应该至少跑 compileall、pytest 和最贴近改动范围的补充验证。

QML 热重载：

```bash
PY_DESKTOP_QML_HOT_RELOAD=1 \
uv run app
```

## 15. 当前边界说明

- `http_capture` 当前仍偏演示/占位，不应视为完整抓包实现。
- API 调试器插件已有 HTTP/WebSocket/Mock 等主链路，但 GraphQL 交互仍不是完整完成态。
- macOS 平台实现和 `.app` 构建脚本已经具备基础结构，仍需要在真实 macOS 环境做权限、热键、应用索引和打包回归。
- 旧的阶段性规划已经合并到本文档；后续如果新增规划，完成后也应回收进长期文档。

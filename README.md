# py-desktop-tools

基于 `PySide6 + Qt Quick (QML)` 的桌面工具箱，核心交互是一个类 uTools 的启动器：应用常驻后台，按 `Alt+Space` 唤起搜索框，按需打开插件、系统工具和应用。

## 快速开始

```bash
uv sync
uv run app
```

打包独立应用：

```bash
uv run build
```

也可以通过安装后的入口运行：

```bash
app
```

QML 热重载：

```bash
PY_DESKTOP_QML_HOT_RELOAD=1 \
uv run app
```

## 文档入口

- [文档索引](docs/README.zh-CN.md)
- [项目设计文档](docs/project-design.zh-CN.md)
- [插件开发教程 / API 参考](docs/plugin-development.zh-CN.md)
- [PyQt/PySide6 + QML 新手教程](docs/pyqt-qml-newbie-guide.zh-CN.md)

## 项目结构

```
src/
  app/
    main.py              # 入口
    app_runtime.py       # 应用运行期组装
    launcher/            # Alt+Space 启动器和插件窗口宿主
    commands/            # 搜索、排序、系统命令、应用索引、动态命令
    plugins/             # Manifest 加载、Runtime 懒加载、Session、后台插件
    platform/            # Windows/macOS/noop 平台能力
    services/            # 纯 Python 应用服务
    storage/             # SQLite 和 dict store 封装
    logging/             # 结构化日志
    concurrency/         # Python 后台任务
    tray/                # 系统托盘
    ui/                  # 通用 QML 控件
    theme/               # 主题令牌
  features/
    api_debugger/
      plugin.json        # Manifest：命令、入口、启动模式
      runtime.py         # Runtime：懒创建 Session/ViewModel
      ApiDebuggerPage.qml    # View
      view_model.py      # ViewModel：QObject + Property/Signal/Slot
      service.py         # Service：纯业务逻辑
    download_manager/        ...
    image_compress/  ...
    json_parser/     ...
    http_capture/  ...
    ftp_sftp_ssh_client/ ...
    qr_code/         ...
    system_settings/ ...
    about/           ...
```

## 分层约定

- Manifest (`plugin.json`) 声明命令、匹配规则、启动模式、QML 页面和 Runtime 入口。
- Runtime 在插件启动时懒加载；后台插件除外。
- Session 表示一次插件交互，负责注入临时 QML context 对象。
- QML 只负责界面、绑定和轻量交互。
- ViewModel (`QObject`) 暴露 `Property`、`Signal`、`Slot` 给 QML。
- Service 是纯 Python 业务层，默认不依赖 QML/Qt。

## QML context

全局 QML context properties：

| Property | ViewModel |
|----------|-----------|
| `app` | `AppViewModel` |
| `launcherBridge` | `LauncherBridge` |

插件 ViewModel 只在插件 Session 活跃或保留期间注入，名称来自 Manifest 的 `contextProperty`，例如 `jsonParserVm`、`qrVm`、`clipboardVm`、`apiDebuggerVm`。

## 验证

```bash
uv run python -m compileall src
uv run pytest
```

Windows / 历史辅助 smoke 脚本仍保留在 `scripts/`，用于补充验证，不作为当前 macOS / zsh 开发环境下的首选入口：

```powershell
scripts\smoke_import.ps1
scripts\smoke_plugin_manifests.ps1
scripts\smoke_storage.ps1
scripts\smoke_tests.ps1
```

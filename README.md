# Suishou（随手）

基于 `PySide6 + Qt Quick (QML)` 的桌面工具箱，核心交互是一个类 uTools 的启动器：应用常驻后台，按 `Alt+Space` 唤起搜索框，按需打开插件、系统工具和应用。

> 原仓库名 `py-desktop-tools`，已迁至 `suishou`。

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
PY_DESKTOP_QML_HOT_RELOAD=1 uv run app
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
    main.py                     # 入口
    app_runtime.py              # 应用运行期组装
    app_bootstrap.py            # 应用上下文装配
    app_context.py              # 运行期对象集合与统一清理
    application_controller.py    # 启动器和插件生命周期用例
    app_relauncher.py           # 应用重启逻辑
    app_view_model.py           # 全局 QML ViewModel（主题/平台信息）
    paths.py                    # 路径工具（项目/资源/数据/缓存）
    qta_icon_provider.py        # qtawesome 图标 QML 提供器
    version.py                  # 版本信息
    launcher/                   # 启动器 QML、Bridge、搜索结果项
    commands/                   # 搜索、排序、上下文匹配、系统/应用命令
    plugins/                    # Manifest、Runtime、Session、后台插件
    platform/                   # 平台抽象（macOS/Windows/noop）
    services/                   # 纯 Python 应用服务
    storage/                    # SQLite 和 dict store 封装
    logging/                    # 结构化日志
    concurrency/                # Python 后台任务
    tray/                       # 系统托盘
    ui/                         # 通用 QML 控件
    theme/                      # QML 主题令牌
  features/
    about/                      # 关于页面
    api_debugger/               # API 调试器（HTTP/WebSocket/Mock）
    app_launcher/               # 系统应用索引
    clipboard/                  # 剪贴板历史
    download_manager/           # 下载管理器
    ftp_sftp_ssh_client/        # FTP/SFTP/SSH 客户端
    http_capture/               # HTTP 抓包
    image_compress/             # 图片压缩
    json_parser/                # JSON 解析格式化
    qml_demo/                   # QML 学习演示
    qr_code/                    # 二维码生成/识别
    quick_launch/               # 快速启动（项目/脚本动作）
    system_settings/            # 系统设置
tests/                          # pytest 测试套件
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
| `app` | `AppViewModel`（主题、平台信息） |
| `launcherBridge` | `LauncherBridge` |

插件 ViewModel 只在插件 Session 活跃或保留期间注入，名称来自 Manifest 的 `contextProperty`，例如 `jsonParserVm`、`qrVm`、`clipboardVm`、`apiDebuggerVm`。

## 构建与发布

### macOS

```bash
# 构建独立 .app
bash tools/build_macos.sh

# 产出：dist/Suishou.app
# 打包为 zip：
ditto -c -k --sequesterRsrc --keepParent dist/Suishou.app "Suishou-$VERSION-macos.zip"
```

### Windows

```powershell
# 构建独立可执行文件
tools\build_windows.ps1

# 产出：dist\Suishou\
# 打包为 zip：
Compress-Archive -Path dist\Suishou -DestinationPath "Suishou-$VERSION-windows.zip"
```

### CI/CD

GitHub Actions 自动构建：打 `v*` tag 触发，产出 macOS-arm64、macOS-x64、Windows 三平台包并发布 Release。

## 验证

```bash
uv run python -m compileall src
uv run pytest
uv run app
```

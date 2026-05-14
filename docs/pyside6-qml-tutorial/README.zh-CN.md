# PySide6 + QML 系列教程 —— 基于 py-desktop-tools 项目

本教程以 **py-desktop-tools** 项目为真实案例，由浅入深覆盖 PySide6 + QML 桌面开发的全套技术。

**适用人群**：有 Python 基础，想系统学习 PySide6 + QML 桌面开发，希望了解类 uTools 启动器、插件系统、MVVM 架构的开发者。

---

## 目录

| 章节 | 内容 | 难度 |
|------|------|------|
| [第 1 章：环境搭建和第一行代码](01-environment-setup.zh-CN.md) | uv、Python 3.13、PySide6 安装，运行项目 | ★☆☆ |
| [第 2 章：QML 基础——从零读懂界面文件](02-qml-basics.zh-CN.md) | Item、Rectangle、Text、属性绑定、锚定布局、import | ★☆☆ |
| [第 3 章：QML 布局系统](03-qml-layout.zh-CN.md) | RowLayout、ColumnLayout、GridLayout、StackLayout、anchors | ★★☆ |
| [第 4 章：QML 与 Python 通信（上）——Signal 和 Slot](04-signal-slot.zh-CN.md) | @Signal、@Slot、setContextProperty、Connections | ★★☆ |
| [第 5 章：QML 与 Python 通信（下）——Property 和数据绑定](05-property-binding.zh-CN.md) | @Property、双向绑定、QVariantList/QVariantMap、notify | ★★☆ |
| [第 6 章：MVVM 架构实战](06-mvvm-architecture.zh-CN.md) | ViewModel、Service 分层、QML 薄化、完整数据流 | ★★★ |
| [第 7 章：启动器原理——从输入框到搜索排序](07-launcher-search.zh-CN.md) | CommandService、评分算法、拼音匹配、上下文识别 | ★★★ |
| [第 8 章：插件系统（上）——Manifest 与懒加载](08-plugin-system-1.zh-CN.md) | plugin.json、Manifest 解析、Runtime 工厂、entrypoint | ★★★ |
| [第 9 章：插件系统（下）——Session、生命周期、资源清理](09-plugin-system-2.zh-CN.md) | Session 管理、QML Context 注入、dispose、close_runtime | ★★★ |
| [第 10 章：后台插件——剪切板案例深入剖析](10-background-plugins.zh-CN.md) | ClipboardBackgroundService、ctx.services、SQLite 持久化 | ★★★ |
| [第 11 章：独立窗口插件——PluginWindow 机制](11-window-plugins.zh-CN.md) | QQmlComponent、createWithInitialProperties、窗口管理 | ★★★ |
| [第 12 章：inline 插件——嵌入启动器的艺术](12-inline-plugins.zh-CN.md) | Loader、mixedMode、activateSelection、moveSelection | ★★★ |
| [第 13 章：QML Loader 与动态组件](13-qml-loader.zh-CN.md) | Loader、Qt.createComponent、QQmlComponent（Python 侧） | ★★☆ |
| [第 14 章：主题系统与设计令牌](14-theme-system.zh-CN.md) | Theme.qml、qmldir、单例模式、深浅色切换、通用组件 | ★★☆ |
| [第 15 章：QML 组件拆分与文件组织](15-component-splitting.zh-CN.md) | 组件拆分原则、property/signal 通信、qmldir 模块化 | ★★★ |
| [第 16 章：全局热键——Windows 底层接入](16-hotkeys.zh-CN.md) | Win32 API、RegisterHotKey、WM_HOTKEY、nativeEventFilter | ★★★ |
| [第 17 章：系统托盘与生命周期管理](17-system-tray.zh-CN.md) | QSystemTrayIcon、信号驱动、背景常驻 | ★★☆ |
| [第 18 章：SQLite 持久化——剪切板存储为例](18-sqlite.zh-CN.md) | sqlite3、CRUD、迁移、配置存储 | ★★☆ |
| [第 19 章：图标系统——qtawesome 与 QML Image Provider](19-icon-system.zh-CN.md) | QQuickImageProvider、image://qta/、SVG 资源 | ★★☆ |
| [第 20 章：热重载——开发效率加速](20-hot-reload.zh-CN.md) | QFileSystemWatcher、clearComponentCache、PY_DESKTOP_QML_HOT_RELOAD | ★★☆ |
| [第 21 章：调试与测试](21-debugging-testing.zh-CN.md) | QQmlComponent 验证、手动回归、内存泄漏排查 | ★★★ |
| [第 22 章：打包与分发](22-packaging.zh-CN.md) | uv、PyInstaller、资源打包 | ★★☆ |

---

## 学习路线

```
第 1 章（环境）→ 第 2-3 章（QML 基础）
  → 第 4-5 章（Python↔QML 通信）
  → 第 6 章（MVVM 架构）
  → 第 7 章（启动器原理）
  → 第 8-9 章（插件系统）
  → 第 10-12 章（插件类型深入）
  → 第 13-19 章（专题技术）
  → 第 20-22 章（工程化）
```

建议按顺序阅读。每章末尾有**实战练习**，用项目代码作为练手材料。

---

## 项目代码阅读顺序

配合教程，建议同步阅读以下代码：

```
1. pyproject.toml                    # 项目配置
2. src/app/main.py                   # 启动入口
3. src/app/launcher/LauncherWindow.qml  # 启动器 UI
4. src/app/launcher/launcher_bridge.py  # QML↔Python 桥
5. src/features/json_parser/         # 最简单的完整插件
6. src/features/qr/                  # ViewModel+Service 分层
7. src/features/clipboard/           # 后台插件
8. src/features/api_test/            # 复杂全功能插件
```

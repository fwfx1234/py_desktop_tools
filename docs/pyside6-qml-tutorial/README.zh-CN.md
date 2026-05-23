# PySide6 + QML 系列教程 —— 基于 py-desktop-tools 项目

本教程以 **py-desktop-tools** 项目为真实案例，逐步解释 PySide6 + QML 桌面开发、MVVM 分层和插件系统。

**适用人群**：有 Python 基础，想系统学习 PySide6 + QML 桌面开发，希望了解类 uTools 启动器、插件系统、MVVM 架构的开发者。

---

## 已完成章节

| 章节 | 内容 | 难度 |
|------|------|------|
| [第 4 章：QML 与 Python 通信（上）——Signal 和 Slot](04-signal-slot.zh-CN.md) | @Signal、@Slot、setContextProperty、Connections | ★★☆ |
| [第 6 章：MVVM 架构实战](06-mvvm-architecture.zh-CN.md) | ViewModel、Service 分层、QML 薄化、完整数据流 | ★★★ |
| [第 8 章：插件系统（上）——Manifest 与懒加载](08-plugin-system-1.zh-CN.md) | plugin.json、Manifest 解析、Runtime 工厂、entrypoint | ★★★ |
| [第 15 章：QML 组件拆分与文件组织](15-component-splitting.zh-CN.md) | 组件拆分原则、property/signal 通信、qmldir 模块化 | ★★★ |

## 待补充主题

- 环境搭建和第一行代码。
- QML 基础和布局系统。
- Property、数据绑定和 `QVariantList`。
- 启动器搜索、排序和上下文识别。
- 插件 Session、生命周期和资源清理。
- 后台插件、独立窗口插件和 inline 插件。
- Loader、主题系统、热键、托盘、SQLite、图标、热重载、调试测试和打包分发。

---

## 学习路线

建议先读已完成章节，再配合 [项目设计文档](../project-design.zh-CN.md) 和应用内 `qml_demo` 插件补齐整体脉络。每章末尾有实战练习，用项目代码作为练手材料。

---

## 项目代码阅读顺序

配合教程，建议同步阅读以下代码：

```
1. pyproject.toml                    # 项目配置
2. src/app/main.py                   # 启动入口
3. src/app/launcher/LauncherWindow.qml  # 启动器 UI
4. src/app/launcher/launcher_bridge.py  # QML↔Python 桥
5. src/features/json_parser/         # 最简单的完整插件
6. src/features/qr_code/             # ViewModel+Service 分层
7. src/features/clipboard/           # 后台插件
8. src/features/api_debugger/            # 复杂全功能插件
```

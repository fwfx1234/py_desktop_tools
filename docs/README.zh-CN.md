# 项目文档索引

这里保留长期有效的项目说明、架构约定和学习资料。阶段性规划在完成后不再单独保留；有价值的结论应沉淀到设计文档或插件开发文档中。

## 推荐阅读顺序

1. [README](../README.md)：项目入口、运行命令和目录概览。
2. [项目设计文档](./project-design.zh-CN.md)：当前架构、模块边界、插件生命周期、平台层、存储、日志和并发约定。
3. [插件开发文档](./plugin-development.zh-CN.md)：新增插件、`plugin.json` 字段、Runtime/Session、launchMode 和动态命令。
4. [PyQt/PySide6 + QML 新手教程](./pyqt-qml-newbie-guide.zh-CN.md)：从 Qt、QML、Signal/Slot 到插件架构的学习路径。

## 教程资料

- [PySide6 + QML 系列教程](./pyside6-qml-tutorial/README.zh-CN.md)：按章节学习 QML 和项目实践。
- [QML 学习演示插件文档](../src/features/qml_demo/docs/README.zh-CN.md)：配合应用内 `qml_demo` 插件边看边试。

## 设计与规范

- [项目设计文档](./project-design.zh-CN.md)：项目主设计文档。
- [插件开发文档](./plugin-development.zh-CN.md)：插件 API 和工程规范。
- [快速启动插件实现计划](./quick-launch-plugin-plan.zh-CN.md)：快速启动项目与脚本动作插件的阶段性实现方案。
- [UI Design System](../design-system/desktop-tools/MASTER.md)：桌面工具 UI 视觉和组件规范。

## 构建与验证

常用命令：

```powershell
uv sync
uv run app
```

Smoke 脚本位于 `scripts/`：

```powershell
scripts\smoke_compile.ps1
scripts\smoke_import.ps1
scripts\smoke_plugin_manifests.ps1
scripts\smoke_storage.ps1
scripts\smoke_tests.ps1
```

独立应用构建脚本：

```powershell
tools\build_windows.ps1
```

macOS：

```bash
tools/build_macos.sh
```

## 文档维护规则

- 新增长期架构约定：更新 [项目设计文档](./project-design.zh-CN.md)。
- 新增插件字段、生命周期或开发规范：更新 [插件开发文档](./plugin-development.zh-CN.md)。
- 新增教学内容：更新教程目录和 `qml_demo` 文档。
- 阶段性规划完成后不要长期保留独立计划文档；只保留仍然指导代码维护的设计结论。

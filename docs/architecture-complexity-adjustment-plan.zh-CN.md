# 架构复杂度收敛调整文档（已归档）

本文档原本用于记录一次阶段性架构收敛计划。该计划中的有效结论已经合并到当前长期设计与 coordinator 去中心化执行文档中，旧正文不再作为执行依据。

当前请以以下文档为准：

- [项目设计文档](./project-design.zh-CN.md)：当前长期架构、模块边界、插件生命周期、平台层、存储、日志和并发约定。
- [Coordinator 去中心化重构执行文档](./coordinator-redesign-execution-plan.zh-CN.md)：本次移除旧 coordinator 文件、拆分应用控制器、插件宿主、热键生命周期和托盘服务的执行记录。
- [插件开发文档](./plugin-development.zh-CN.md)：插件开发教程、Runtime/Session、launchMode、动态命令和清理约定。

维护规则：

- 后续不要按旧计划恢复 `launcher_runtime_coordinator.py`、`plugin_surface_coordinator.py`、`hotkey_coordinator.py` 或 `tray_coordinator.py`。
- 运行期用户意图入口是 `ApplicationController`。
- 插件 UI 宿主是 `PluginHostService`。
- 热键注册、刷新和剪贴板热键配置监听属于 `HotkeyLifecycle` 与 `HotkeyService`。
- 应用生命周期调度和后台插件启动属于 `ApplicationContext`。

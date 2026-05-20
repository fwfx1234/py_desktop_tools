# 快速启动插件实现计划

本文记录 `quick-launch` 插件的实现方案。该插件用于配置项目和脚本动作，让常用命令、脚本、目录、URL 能从主启动器直接搜索并执行。

## 1. 目标

- 新增内置插件 `quick-launch`，作为后台插件常驻。
- 启动时读取快速启动配置，并把启用动作注册为启动器动态命令。
- 用户可在主启动器中直接搜索动作并执行。
- 插件窗口提供项目分组、全局动作列表、动作编辑、参数表单和运行历史。
- 第一版优先支持当前 macOS/zsh 开发环境，同时为后续跨平台实现预留数据字段。

## 2. 功能范围

### 2.1 插件形态

- 插件目录：`src/features/quick_launch/`。
- Manifest：
  - `id`: `quick-launch`
  - `activation`: `background`
  - `launchMode`: `window`
  - `contextProperty`: `quickLaunchVm`
- 后台启动后注册动态命令；窗口用于管理配置和查看历史。
- 数据按项目分组展示，同时提供全局动作列表。

### 2.2 动作类型

第一版支持四类动作：

- `shell`：执行一段 shell 命令。
- `script_file`：执行一个脚本文件。
- `open_path`：打开本地文件或目录。
- `open_url`：打开 URL。

每个动作支持以下配置：

- 名称、所属项目、描述、图标。
- 关键词、前缀、启用状态、排序。
- 命令文本、脚本路径、文件路径或 URL。
- 工作目录。
- 环境变量。
- 超时时间。
- 反馈方式：`history`、`terminal`、`silent`。

### 2.3 参数表单

- 动作命令中使用 `${name}` 形式声明参数占位符。
- 当动作包含占位符时，启动器命中后打开插件窗口并显示参数表单。
- 用户提交参数后再执行动作。
- shell/script 动作替换参数时默认做 shell quote，避免用户输入被当作裸 shell 片段执行。

## 3. 数据模型

使用插件私有 SQLite 数据库保存配置和运行历史。

### 3.1 `quick_launch_projects`

保存项目分组：

- `id`
- `name`
- `description`
- `root_path`
- `sort_order`
- `created_at`
- `updated_at`

### 3.2 `quick_launch_actions`

保存快速动作：

- `id`
- `project_id`
- `name`
- `description`
- `kind`
- `command`
- `path`
- `url`
- `cwd`
- `env_json`
- `keywords_json`
- `prefixes_json`
- `icon`
- `feedback_mode`
- `timeout_sec`
- `enabled`
- `sort_order`
- `created_at`
- `updated_at`

预留字段：

- `shell_by_platform_json`

该字段第一版不强依赖，仅用于后续 Windows/Linux 扩展。

### 3.3 `quick_launch_runs`

保存运行记录：

- `id`
- `action_id`
- `status`
- `exit_code`
- `stdout`
- `stderr`
- `duration_ms`
- `started_at`
- `finished_at`
- `message`

运行输出策略：

- `stdout` 和 `stderr` 各最多保留 64KB。
- 超出内容截断并在 `message` 标记。
- 可按时间倒序展示最近运行记录。

## 4. 执行与动态命令

### 4.1 动态命令注册

- `on_background_start(ctx)` 读取所有启用动作。
- 对每个动作调用 `ctx.platform.commands.register()`。
- 动态命令 payload 使用 `{ "actionId": "..." }`。
- 动作保存、删除、启用或停用后刷新注册表。
- `on_background_stop()` 调用 `unregister_all()` 注销本插件命令。

### 4.2 启动器执行路径

- 无参数动作：
  - 动态命令使用 `launchMode: "none"`。
  - Runtime 收到 `actionId` 后直接执行。
  - 执行后返回 `NoopPluginSession`。
- 带参数动作：
  - 动态命令使用 `launchMode: "window"`。
  - Runtime 根据 `actionId` 打开参数表单。
  - 参数提交后由 ViewModel 调用 Service 执行。

### 4.3 macOS/zsh 执行策略

- `shell` 默认使用 `/bin/zsh -lc <command>`。
- `script_file` 使用脚本路径执行，并支持工作目录和参数占位符。
- `open_path` 复用平台 `open_path()`。
- `open_url` 复用平台 `open_url()`。
- 捕获模式默认超时 300 秒。
- `timeout_sec = 0` 表示不主动超时。

### 4.4 反馈方式

- `history`：
  - 后台执行并捕获 stdout、stderr、退出码、耗时。
  - 写入运行历史。
- `terminal`：
  - 使用 macOS Terminal 打开并执行命令。
  - 不捕获完整输出，只记录基础启动状态。
- `silent`：
  - 后台执行。
  - 只记录成功、失败和基础错误信息。

## 5. UI 设计

插件窗口采用工作型工具布局：

- 左侧：项目列表、搜索、新建项目。
- 右侧上方：全局动作列表，可按项目、类型、启用状态过滤。
- 右侧下方或弹窗：动作编辑表单。
- 历史区：展示最近运行记录、状态、耗时、退出码、stdout/stderr 预览。
- 参数表单：根据 `${name}` 占位符动态生成输入项。

核心交互：

- 新建、编辑、复制、删除项目。
- 新建、编辑、复制、删除动作。
- 启用或停用动作。
- 从管理页立即运行动作。
- 查看运行历史和错误输出。

## 6. 测试计划

- 仓储测试：
  - 项目增删改查。
  - 动作增删改查。
  - 启用过滤和排序。
  - 运行历史写入与截断。
- 参数测试：
  - `${name}` 占位符提取。
  - 参数替换。
  - shell quote。
  - 缺失参数校验。
- 执行测试：
  - `shell`、`script_file`、`open_path`、`open_url` 分发。
  - subprocess 使用 fake/mock。
  - 平台 API 使用 fake/mock。
- 动态命令测试：
  - 后台启动注册动态命令。
  - 保存、删除、启停动作后刷新注册。
  - 后台停止后注销动态命令。
- 验证命令：

```bash
uv run pytest tests/features/quick_launch
uv run python -m compileall src
```

## 7. 假设与边界

- 用户配置的本地脚本视为可信，不做危险命令拦截或二次确认。
- 长时间常驻命令建议使用 `terminal` 反馈方式。
- 捕获模式主要面向有明确退出结果的脚本。
- 第一版不做配置导入导出。
- 实现完成后，应把长期有效的结论沉淀到项目设计文档或插件开发文档；该计划文档可按项目文档维护规则清理或归档。

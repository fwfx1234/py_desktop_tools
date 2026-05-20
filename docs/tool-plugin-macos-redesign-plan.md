# 工具插件 mac 化重设计实施计划

## 背景与目标

当前 `二维码`、`JSON 解析`、`下载工具`、`抓包工具`、`图片压缩` 五个工具插件已经具备基础能力，但页面普遍以表单和列表直接堆叠为主，缺少 mac 工具类应用常见的紧凑工具栏、分栏信息结构、稳定状态反馈和高频操作入口。部分功能也停留在 MVP 阶段，例如抓包工具当前只生成模拟请求，下载和图片压缩缺少输出定位与批量结果反馈。

本次改造目标是保留现有插件架构和启动方式，在 macOS 开发环境下重新设计这五个插件的界面与核心交互，使其更接近专业桌面工具：信息密度更高、操作路径更短、状态更清晰，并补齐必要的 ViewModel 和 Service 能力。

## 改造范围

- 二维码：保留 `inline_view` 打开方式，优化生成、扫描、历史和导出体验。
- JSON 解析：保留独立窗口，优化编辑器分栏、格式化、压缩、查询和错误反馈。
- 下载工具：保留独立窗口，改为自动保存为主，增强任务队列管理和 Finder 定位。
- 抓包工具：保留独立窗口，从模拟数据升级为真实本地代理，支持 HTTPS 解密流程。
- 图片压缩：保留 `inline_view` 打开方式，优化拖放、批量结果、自动保存和输出目录定位。

不在本次范围内：

- 不重写 launcher 或插件宿主架构。
- 不改变 QR 和图片压缩的默认 `launchMode`。
- 不重做全局设计系统，只复用并适度组合现有 `Theme` 和 `app/ui` 组件。
- 不自动修改 macOS 系统代理、钥匙串信任或浏览器代理配置。

## 公共 UI 设计原则

- 页面结构统一为顶部工具栏、主内容区、底部状态区；窗口插件优先使用左右分栏，内嵌插件保持紧凑但保留清晰主操作区。
- 使用 macOS 字体偏好：界面文本优先 `SF Pro Text`，代码和结构化文本优先 `SF Mono`，不可用时回退到现有 `Theme.fontFamily`。
- 优先使用 `UiIcon` 和 `image://qta/` 图标按钮承载高频操作，并提供 Tooltip；明确命令仍使用文字按钮。
- 固定工具栏、列表行、预览区域和状态栏尺寸，避免长 URL、长 JSON、长文件名导致布局跳动。
- 长文本默认省略或中间省略，详情区再展示完整内容。
- 深浅色均使用 `Theme.token(...)`，不引入单独色板。
- 空状态、进行中状态、成功状态、失败状态都要有明确视觉反馈。
- 自动保存类操作完成后提供“打开 Finder”和“复制路径”入口。

## 分插件实施方案

### 二维码

- 将页面改为 `生成 / 扫描 / 历史` 三个紧凑 Tab，顶部显示输入来源和当前状态。
- 生成页左侧为文本输入，右侧为固定比例二维码预览；输入变化只更新预览，不立即写历史。
- 增加显式操作：复制二维码内容、保存二维码图片、清空输入。
- 保存二维码默认写入 `~/Downloads/PyDesktopTools/QR/`，文件名使用时间戳和内容摘要。
- 扫描页支持文件选择和拖放图片，扫描成功后展示结果、复制结果、保存到历史。
- 历史页支持搜索、复制条目、删除单条、清空、导出；导出默认保存到自动目录。
- 历史写入规则调整为：扫描成功、保存二维码、复制生成内容等显式动作才写入，避免输入时持续刷历史。

### JSON 解析

- 页面改为顶部工具栏加左右 SplitView：左侧输入，右侧输出或查询结果。
- 工具栏提供格式化、压缩、执行查询、复制输出、清空、从剪贴板填充。
- 输入区使用等宽字体、无换行默认展示，并保留横向滚动。
- 输出区支持格式化 JSON、压缩 JSON 和 JSONPath 查询结果三种模式。
- 底部状态区展示解析状态、字符数、对象/数组规模、错误位置。
- 错误反馈尽量包含行列号、错误摘要和失败阶段。
- 保留现有 JSONPath 子集，不在本轮引入完整 JSONPath 第三方库，避免扩大解析语义。

### 下载工具

- URL 输入位于顶部工具栏，粘贴 URL 后可直接回车创建任务。
- 默认自动保存到 `~/Downloads/PyDesktopTools/Downloads/`，文件名优先从响应头 `Content-Disposition` 推断，其次从 URL path 推断，最后使用时间戳。
- 任务列表展示文件名、来源域名、状态、进度、速度、已下载/总大小、耗时。
- 任务操作包括取消、重试、移除、打开文件、在 Finder 中显示。
- 增加“清空已完成”和“清空失败”操作，避免误删正在下载任务。
- Service 层保留取消能力，补充文件名推断、任务元数据、失败原因、完成路径。
- 下载完成或失败后通过状态区展示最近事件。

### 抓包工具

- 引入 `mitmproxy` 作为真实本地代理核心依赖。
- 默认监听 `127.0.0.1:8899`；端口占用时自动尝试后续端口，并在界面显示实际端口。
- 首次使用展示证书状态、证书路径和代理配置提示；只提供打开证书目录、复制代理地址，不自动修改系统设置。
- 主界面左侧为请求列表，右侧为详情面板；列表支持方法、域名、路径、状态、类型、大小、耗时。
- 详情面板分 Tab 展示 Overview、Request Headers、Request Body、Response Headers、Response Body。
- 支持过滤：关键字、方法、状态码范围、内容类型、只看错误。
- 支持清空、暂停记录、复制 cURL、复制 URL、保存响应正文。
- HTTPS 解密依赖用户信任 mitmproxy CA；未信任时仍可展示 CONNECT 或有限元数据，并在状态区提示。
- 后台代理必须可停止，窗口关闭或插件销毁时释放端口和后台任务。

### 图片压缩

- 页面改为拖放选择区、参数工具栏、结果列表三段式。
- 支持拖放图片和文件选择，去重后显示待处理文件列表。
- 模式保留 `视觉无损` 和 `普通压缩`，质量滑块固定宽度并显示当前百分比。
- 默认输出到 `~/Downloads/PyDesktopTools/ImageCompress/`，保留原文件名并追加压缩后缀，冲突时自动编号。
- 结果从纯文本升级为结构化列表：原大小、压缩后大小、节省比例、输出路径、错误原因。
- 完成后显示总文件数、成功数、失败数、总节省体积。
- 提供打开输出目录、复制输出目录、清空列表、移除单个待处理文件。

## ViewModel / Service / API 变化

### QR

- 新增预览生成和显式保存分离的 ViewModel 方法。
- 新增复制文本、保存图片、删除历史单条、打开输出目录相关 Slot。
- Service 层生成二维码时返回图片路径，保存时写入自动目录并记录历史。

### JSON

- `processJson` 保留兼容，内部增加模式参数或新增 Slots：格式化、压缩、查询。
- 输出结果携带状态信息：错误文本、行列号、统计信息。
- 复制仍通过现有剪贴板能力实现。

### 下载

- 保留 `downloadFile(url, savePath)` 兼容旧调用。
- 新增 `downloadUrl(url)` 使用自动保存策略。
- 新增 `retryDownloadTask(id)`、`removeDownloadTask(id)`、`revealDownload(id)`、`openDownloadedFile(id)`。
- 任务数据增加 `fileName`、`domain`、`savePath`、`totalBytes`、`writtenBytes`、`elapsedMs`、`error`。

### 抓包

- runtime 改为接收 `PluginContext`，ViewModel 需要平台 API 和插件数据目录。
- Service 层新增代理生命周期：start、stop、pause、resume、clear。
- 新增请求详情模型和选中请求 Slot。
- 新增证书路径、代理地址、运行状态、错误状态信号。

### 图片压缩

- `compressImages(files, quality, mode)` 保留兼容。
- 新增结构化结果信号，例如 `compressionResultsUpdated(QVariantList)` 和 `compressionSummaryUpdated(QVariantMap)`。
- Service 层返回逐文件结果，而不是只返回汇总文本。
- 新增打开输出目录和复制输出目录能力。

## 依赖变化

- 新增 `mitmproxy`，用于抓包工具真实代理和 HTTPS 解密。
- dry-run 检查显示 Python 3.13 环境可解析 `mitmproxy==12.2.3`，会带入 `mitmproxy-macos`、`mitmproxy-rs`、`aioquic`、`h11`、`h2`、`brotli`、`zstandard` 等依赖。
- 实施时使用 `uv add mitmproxy` 更新 `pyproject.toml` 和 `uv.lock`。
- 现有 `opencv-python`、`qrcode`、`Pillow`、`requests`、`pyperclip` 继续沿用。

## 测试计划

- 新增或补齐 focused tests：
  - `tests/features/qr/`：预览不写历史、保存写历史、扫描结果、导出路径。
  - `tests/features/json_parser/`：格式化、压缩、查询、错误位置、复制失败处理。
  - `tests/features/download/`：自动文件名推断、任务状态、取消、重试、失败原因。
  - `tests/features/image_compress/`：输出路径、逐文件结果、失败文件、汇总统计。
  - `tests/features/packet_capture/`：代理状态转换、flow 到 row/detail 的转换、过滤逻辑。
- 抓包服务单元测试使用 fake mitmproxy flow，不依赖真实外网。
- HTTPS 解密和证书信任作为手动验证项或 slow 集成测试，不放入默认测试路径。
- 实施完成后运行：

```bash
uv run pytest tests/features/qr tests/features/json_parser tests/features/download tests/features/image_compress tests/features/packet_capture
uv run python -m compileall src
```

- 手动启动验证：

```bash
uv run app
```

重点检查五个插件在 macOS 下的窗口尺寸、内嵌尺寸、深浅色、长文本、拖放、自动保存、Finder 操作和关闭清理。

## 假设与边界

- 自动保存目录固定为 `~/Downloads/PyDesktopTools/<PluginName>/`，本轮不做持久化目录设置。
- 抓包工具只在用户点击启动后运行，不后台常驻。
- 应用不自动修改系统代理、不自动安装或信任证书，只提供可操作路径和清晰状态。
- HTTPS 正文解密必须依赖用户完成证书信任；未完成时功能降级并明确提示。
- QR 和图片压缩仍按内嵌插件适配小尺寸，不强制弹出独立窗口。
- 现有插件 ID、命令 ID、contextProperty 保持不变，避免影响命令索引和外部调用。
- 本计划是后续实现的依据，不包含实际 UI 和服务代码变更。

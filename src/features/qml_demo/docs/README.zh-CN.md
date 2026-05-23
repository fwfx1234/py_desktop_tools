# QML 学习演示插件 — 配套学习文档

## 如何使用

1. 启动应用：`uv run app`
2. 按 `Alt+Space` 打开启动器
3. 搜索 `QML 学习演示` 或 `demo`
4. 进入插件，左侧边栏选择学习主题

## 17 课内容概要

| 课程 | 内容 | 学到的技术 |
|------|------|-----------|
| 第 1 课：基础元素 | Rectangle、Text、Image、Item | QML 四大基础元素 |
| 第 2 课：布局系统 | RowLayout、ColumnLayout、Grid、anchors | 声明式布局 |
| 第 3 课：属性绑定 | 双向绑定、声明式绑定、颜色选择器 | QML 最核心特性 |
| 第 4 课：信号与槽 | Signal → QML Connections、@Slot → Python | Python ↔ QML 通信 |
| 第 5 课：控件大全 | UiButton、UiTextField、UiSwitch 等 | 通用 UI 组件 |
| 第 6 课：自定义组件 | property + signal 封装、component 关键字 | 组件化开发 |
| 第 7 课：ListView | model/delegate 模式、数据过滤 | 数据驱动列表 |
| 第 8 课：主题系统 | Theme.token()、深浅色切换 | 设计令牌 |
| 第 9 课：动画效果 | Behavior、NumberAnimation、RotationAnimation | 声明式动画 |
| 第 10 课：Dialog 弹窗 | MessageDialog、FileDialog、Popup | 弹窗系统 |
| 第 11 课：Loader 加载 | Loader、动态组件、source 切换 | 按需加载 |
| 第 12 课：TabBar 选项卡 | TabBar、TabButton、StackLayout | 多页面切换 |
| 第 13 课：Timer + 状态 | Timer、states、transitions | 定时器与状态机 |
| 第 14 课：Slider 滑块 | Slider、SpinBox、RangeSlider | 数值输入 |
| 第 15 课：ToolTip/Menu | ToolTip、Menu、MenuItem | 辅助交互 |
| 第 16 课：Gradient/Flow | Gradient、Flow、GridLayout | 视觉与自适应排布 |
| 第 17 课：Keys/Shortcut | Keys、Shortcut、focus | 键盘事件 |

## 代码结构

```
src/features/qml_demo/
├── plugin.json              # 插件清单
├── runtime.py               # Runtime 工厂
├── view_model.py            # 交互式 ViewModel（@Property + @Slot）
├── QmlDemoPage.qml          # 主页面（侧边栏 + StackLayout）
├── pages/                   # 17 个演示页面
│   ├── BasicElementsPage.qml
│   ├── LayoutPage.qml
│   ├── BindingPage.qml
│   ├── SignalsPage.qml
│   ├── ControlsPage.qml
│   ├── ComponentsPage.qml
│   ├── ListViewPage.qml
│   ├── ThemePage.qml
│   ├── AnimationPage.qml
│   ├── DialogPage.qml
│   ├── LoaderPage.qml
│   ├── TabBarPage.qml
│   ├── TimerStatePage.qml
│   ├── InputWidgetsPage.qml
│   ├── TooltipMenuPage.qml
│   ├── GradientFlowPage.qml
│   └── KeysShortcutPage.qml
└── docs/
    └── README.zh-CN.md      # 本文档
```

## 学习要点

### 每个页面都遵循同一模式

```
Flickable {                      ← 可滚动容器
    ColumnLayout {               ← 垂直布局
        Label { }                ← 标题
        Label { }                ← 知识点说明
        Rectangle { }            ← 代码示例
        [交互式 Demo]            ← 活例演示
        Rectangle { }            ← 小结
    }
}
```

### ViewModel 交互

`view_model.py` 提供了：
- `count` / `demoColor` / `formName` / `formEmail` — `@Property` 双向绑定
- `increment()` / `decrement()` / `resetCount()` — `@Slot` 命令
- `filterItems(query)` / `submitForm()` — 业务操作
- `messageReceived` — `Signal` 通知
- `items` — `@Property` 列表数据

### 和完整插件（api_debugger）的对比

| 方面 | qml-demo | api_debugger |
|------|---------|---------|
| QML 结构 | 17 页演示页面 | 单页入口，多组件拆分 |
| ViewModel 行数 | ~100 | ~970 |
| Service | 无 | 5 个 Service 类 |
| 组件数量 | 17 个主题页面 | 16 个组件 |
| launchMode | inline_view | window |
| 适合 | 学习 QML 基础 | 学习复杂 MVVM |

## 延伸学习

1. 读 `docs/project-design.zh-CN.md` — 当前项目架构和插件边界
2. 读 `src/features/json_parser/` — 最简单的完整插件
3. 读 `src/features/clipboard/` — 后台插件案例
4. 读 `src/features/api_debugger/` — 复杂全功能插件案例
5. 读教程系列 `docs/pyside6-qml-tutorial/` — 从零开始的完整教程

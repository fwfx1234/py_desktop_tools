# 第 6 章：MVVM 架构实战

本章以 api_debugger 插件为案例，深入讲解项目中的 MVVM（Model-View-ViewModel）分层设计。

---

## 6.1 为什么需要 MVVM

### 问题：代码全堆在 QML 里

```qml
// ❌ 反模式：1400 行 JS 逻辑塞在 QML 文件里
Item {
    id: root
    property var queryParams: [...]
    property var endpointTabs: [...]
    property var collectionTree: [...]
    // ... 40 个属性

    function sendCurrent() { /* 30 行业务逻辑 */ }
    function persistCurrentTabDraft() { /* 30 行 */ }
    function applyEndpointTab(index) { /* 40 行 */ }
    // ... 70 个函数
}
```

后果：文件 2900 行，难以维护，JS 函数无法单元测试，换个 UI 就得重写逻辑。

### 解决：MVVM 三层分离

```
┌─ QML (View) ────────────────┐
│ 布局、样式、用户交互           │  ← 声明式，无业务逻辑
│ 绑定到 apiDebuggerVm.xxx         │
│ onClicked: apiDebuggerVm.doSomething() │
└──────────────────────────────┘
         ↕ Signal/Slot/Property
┌─ ViewModel (Python QObject) ─┐
│ @Property 持有全部数据状态     │  ← 可测试
│ @Slot 执行业务逻辑             │
│ 调用 Service，emit 通知 View   │
└──────────────────────────────┘
         ↕ 纯 Python 调用
┌─ Service (纯 Python) ────────┐
│ HTTP 请求、数据库、算法       │  ← 无 Qt 依赖
│ 可独立运行、可单独测试         │
└──────────────────────────────┘
```

---

## 6.2 状态归谁管？

这是 MVVM 最核心的决策。状态分两类：

| 类型 | 例子 | 放哪 | 原因 |
|------|------|------|------|
| **数据状态** | `queryParams`、表单值、列表数据 | ViewModel | 换 UI 框架也有效 |
| **UI 状态** | 哪个 tab 展开、侧边栏宽度 | QML | 纯视觉效果 |

```python
# ViewModel 持有数据状态
class ApiDebuggerViewModel(QObject):
    editorChanged = Signal()

    def __init__(self):
        super().__init__()
        self._query_params: list[dict] = []
        self._endpoint_tabs: list[dict] = []
        self._current_body_mode: int = 0
        self._collection_tree: list[dict] = []
        # ... 29 个内部状态

    # 每个状态都通过 @Property 暴露
    def _get_query_params(self): return self._query_params
    def _set_query_params(self, v):
        if self._query_params != v:
            self._query_params = list(v)
            self.editorChanged.emit()
    queryParams = Property("QVariantList", _get_query_params, _set_query_params, notify=editorChanged)
```

```qml
// QML 只保留 UI 专属属性
Item {
    id: root
    property int currentTab: 0            // 哪个子 tab 打开
    property real sidebarWidth: 260       // 侧边栏拖拽宽度
    property bool showMagicPanel: false   // 魔法面板是否显示
    // 注意：没有任何数据相关的 root property
}
```

---

## 6.3 数据流标准模式

### 模式 1：读取（View → ViewModel）

```qml
// QML：直接绑定到 ViewModel 属性
KvTableSection {
    rows: apiDebuggerVm.queryParams    // 读 ViewModel
}
```

### 模式 2：用户操作（View → ViewModel → Service）

```qml
// QML：只发信号，不处理逻辑
onSendClicked: {
    apiDebuggerVm.sendRequest({
        method: requestActionBar.getMethodText(),
        url: requestActionBar.getUrlText(),
        headersText: ApiUtils.buildHeaderText(apiDebuggerVm.headersRows),
        // ... 组装数据
    })
}
```

```python
# ViewModel：处理逻辑
@Slot("QVariantMap")
def sendRequest(self, data: dict) -> None:
    method = str(data.get("method") or "GET")
    headers_text = str(data.get("headersText") or "")
    # 组装请求 → 调 Service
    if request_mode == "websocket":
        self.wsSend(tab_id, body_text, ws_encoding)
    else:
        self.sendApi(method, url, ...)
```

### 模式 3：结果返回（Service → ViewModel → View）

```python
# Service 返回结果 → ViewModel emit Signal
title, body, details = self._service.send_api(...)
self.apiResponseReady.emit(title, body, details)
```

```qml
// QML Connections 接收
Connections {
    target: apiDebuggerVm
    function onApiResponseReady(title, bodyText, details) {
        responsePanel.detailTab = 0
    }
}
```

---

## 6.4 QML 胶水代码的边界

QML 中仍需要少量的 JS 函数，但它们**只做数据组装，不做业务判断**：

```qml
// ✅ 正确：把 QML 元素的值读出来，组装成 dict，传给 ViewModel
function sendCurrent() {
    apiDebuggerVm.sendRequest({
        method: requestActionBar.getMethodText(),
        url: requestActionBar.getUrlText(),
        paramsText: ApiUtils.buildKvText(apiDebuggerVm.pathParams) + "\n" +
                    ApiUtils.buildKvText(apiDebuggerVm.queryParams),
        // ... 只做数据读取和组装
    })
}

// ❌ 错误：在 QML 里做业务判断
function sendCurrent() {
    if (root.mockMode) { /* 复杂分支 */ }
    if (currentBodyModeIndexIsFile(root.currentBodyMode)) { /* ... */ }
    // 这些逻辑应该在 ViewModel 的 @Slot 里
}
```

---

## 6.5 api_debugger 重构前后对比

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| ApiDebuggerPage.qml 行数 | 2903 | 508 |
| QML 中 JS 函数数量 | ~80 | ~10（都是胶水组装） |
| 数据属性在哪 | QML root property | ViewModel @Property |
| 业务逻辑在哪 | QML function | ViewModel @Slot |
| 组件文件数 | 10 | 16 |

### 重构前

```qml
Item {
    id: root
    property var queryParams: [ { enabled: true, key: "", value: "" } ]  // 40 个属性
    property var headersRows: [...]
    property var endpointTabs: [...]

    function updateSectionRowEnabled(sectionName, rowIndex, checked) {  // 70 个函数
        var rows = rowsBySection(sectionName).slice()
        rows[rowIndex].enabled = checked
        commitSectionRows(sectionName, rows)
    }
    function sendCurrent() { /* 30 行 */ }
    function persistCurrentTabDraft() { /* 30 行 */ }
}
```

### 重构后

```qml
Item {
    id: root
    property int currentTab: 0     // 只有 6 个 UI 属性

    function sendCurrent() {       // 只有 5 个胶水函数
        apiDebuggerVm.sendRequest({ method: ..., url: ..., ... })
    }

    KvTableSection {
        rows: apiDebuggerVm.queryParams  // 组件绑定到 ViewModel
    }
}
```

---

## 6.6 ViewModel 设计清单

写好一个 ViewModel，需要覆盖这些：

```python
class MyViewModel(QObject):
    # 1. Signals —— 通知 View 数据变化
    itemsChanged = Signal()
    countChanged = Signal()
    errorOccurred = Signal(str)

    # 2. Properties —— 暴露数据给 View 绑定
    items = Property("QVariantList", _get_items, _set_items, notify=itemsChanged)
    count = Property(int, _get_count, _set_count, notify=countChanged)

    # 3. Slots —— 接收 View 的用户操作
    @Slot(str)
    def addItem(self, name: str): ...
    @Slot(int)
    def removeItem(self, index: int): ...

    # 4. dispose —— 清理资源
    def dispose(self):
        self._disposed = True
        if self._service:
            self._service.close()
```

---

## 6.7 实战练习

1. 打开 `src/features/json_parser/view_model.py`，数一数有几个 Signal、Slot、Property
2. 找到 `JsonParserPage.qml` 中调用 ViewModel Slot 的地方
3. 找到 `JsonParserPage.qml` 中绑定 ViewModel Property 的地方
4. 对比 `src/features/api_debugger/view_model.py`，理解复杂 ViewModel 的结构
5. 尝试给 JSON 解析插件加一个新功能：从 ViewModel 暴露一个 `wordCount` Property

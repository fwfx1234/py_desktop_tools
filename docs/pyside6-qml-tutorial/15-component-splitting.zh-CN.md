# 第 15 章：QML 组件拆分与文件组织

本章以 api_test 插件从 2900 行拆分到 508 行的真实过程，讲解 QML 组件化的全部套路。

---

## 15.1 拆分前的典型症状

```qml
// ApiTestPage.qml — 2903 行
Item {
    id: root
    property var queryParams: [...]       // ~40 个属性
    property var headersRows: [...]
    property var endpointTabs: [...]

    function sendCurrent() { /* ... */ }   // ~80 个函数
    function persistCurrentTabDraft() { /* ... */ }
    function buildKvText(items) { /* ... */ }

    // 视觉树 ~1450 行 — 全部内联
    ColumnLayout {
        RowLayout {
            Item {
                ApiCollectionSidebar { }
            }
            Rectangle { } // splitter
            ColumnLayout {
                Rectangle { // endpoint tabs bar — 260 行
                    RowLayout {
                        Rectangle { } // scroll left
                        Flickable {
                            Repeater {
                                delegate: Rectangle {
                                    // 每个 tab 的 UI — 80 行
                                }
                            }
                        }
                        // ... 更多
                    }
                }
                // ... 9 个 tab 的内容，每个 50-200 行
                // ... 响应面板 250 行
            }
        }
    }
    // ... 5 个 popup / dialog
}
```

**问题**：一个文件承担了 View + ViewModel + Controller 的全部职责。

---

## 15.2 拆分策略：5 种模式

| 模式 | 怎么拆 | 什么时候用 | 项目中的例子 |
|------|--------|-----------|-------------|
| **模式 1**：提取重复模式 | 同样的 QML 块出现 ≥3 次 → 抽成组件 | 5 处 K-V 表格 | `KvTableSection.qml` |
| **模式 2**：按功能分文件 | 大块独立 UI 区域 → 独立文件 | 响应面板、Body Tab | `ApiResponsePanel.qml`、`ApiBodyTab.qml` |
| **模式 3**：纯函数提取 | 不依赖 QML 上下文的 JS → `.pragma library` | 树操作、序列化 | `api_utils.js` |
| **模式 4**：业务逻辑迁移 | 依赖 QML 上下文的逻辑 → Python ViewModel `@Slot` | sendRequest、persistTab | `view_model.py` |
| **模式 5**：数据状态上移 | QML root property → ViewModel `@Property` | queryParams、environments | `ApiTestViewModel` |

---

## 15.3 模式 1：提取重复模式 → KvTableSection

**拆分前**（5 处完全相同的代码，每处 ~44 行）：

```qml
// 5 次重复：Params、Path、Body、Headers、Cookies
ColumnLayout {
    ApiKvTableHeader {
        dark: root.dark
        textMuted: root.textMuted
        keyWidth: 220; descWidth: 180
        // ...
    }
    ScrollView {
        ColumnLayout {
            Repeater {
                model: root.queryParams  // 不同点：绑定的数据
                delegate: ApiKvRow {
                    onKeyCommitted: root.updateSectionRowKey("query", index, keyText, true)
                    // 不同点：section 名字和信号处理
                }
            }
        }
    }
}
```

**拆分后**（1 个组件，5 处使用，每处 ~16 行）：

```qml
// components/KvTableSection.qml
ColumnLayout {
    id: root
    property var rows: []
    property bool showTypeSelector: false
    property int keyWidth: 210
    // ... 可配置属性

    signal rowKeyCommitted(int index, string keyText)
    signal rowValueCommitted(int index, string valueText)
    // ... 所有可能的信号

    ApiKvTableHeader { /* 绑定到 root 属性 */ }
    ScrollView {
        ColumnLayout {
            Repeater {
                model: root.rows
                delegate: ApiKvRow {
                    onKeyCommitted: root.rowKeyCommitted(index, keyText)
                }
            }
        }
    }
}
```

**使用**：

```qml
KvTableSection {
    rows: apiTestVm.queryParams
    showTypeSelector: true
    keyWidth: 220; descWidth: 180
    dark: root.dark
    onRowKeyCommitted: (i, k) => apiTestVm.editSectionRowKey("query", i, k)
}
```

**效果**：5 x 44 = 220 行 → 1 x 98 (组件) + 5 x 16 = 178 行，消除重复，修改一处生效全部。

---

## 15.4 模式 2：按功能分文件 → 独立组件

### 判断标准

| 块大小 | 做法 |
|--------|------|
| < 30 行 | 保持内联 |
| 30-100 行 | 看是否引用外部 ID（是→保持，否→拆分） |
| > 100 行 | 拆分 |

### 拆分前：响应面板内联 ~250 行

```qml
// ApiTestPage.qml 中
ColumnLayout {
    // 响应标题栏 — 50 行
    Rectangle { RowLayout { Label { }; Switch { }; Switch { } } }
    // Tab 栏 — 60 行
    Rectangle { RowLayout { Repeater { delegate: Rectangle { } } } }
    // 空状态 — 30 行
    ColumnLayout { Rectangle { Image { } }; Label { } }
    // 内容区 — 100 行
    Rectangle {
        UiTextArea { }
        Flickable { ColumnLayout { Repeater { delegate: Rectangle { ColumnLayout { } } } } }
    }
}
```

**拆分后：独立的 ApiResponsePanel.qml**

```qml
// components/ApiResponsePanel.qml
ColumnLayout {
    id: root
    property bool dark: false
    property string bodyText: ""
    // ... 暴露属性和函数

    function applyDetails(title, bodyTextValue, details) {
        titleText = title
        bodyText = bodyTextValue || ""
        // ... 处理日志条目
    }

    function responseHasContent() {
        return bodyText.length > 0 || headersText.length > 0 || ...
    }

    // 视觉树 — 完整的响应面板
    Rectangle { /* 标题栏 */ }
    Rectangle { /* Tab 栏 */ }
    Rectangle { /* 内容区 */ }
}
```

**在根文件中使用**：

```qml
ApiResponsePanel {
    id: responsePanel
    anchors.left: parent.left; anchors.right: parent.right
    anchors.top: verticalSplitter.bottom; anchors.bottom: parent.bottom
    dark: root.dark; panelBg: root.panelBg
    mockMode: apiTestVm.mockMode
    onMockModeToggled: apiTestVm.mockMode = checked
}
```

**效果**：根文件 -250 行。

---

## 15.5 模式 3：纯函数提取 → .pragma library

### 什么是 .pragma library

```javascript
// api_utils.js
.pragma library

function normalizeMethod(methodText) {
    if (!methodText) return "GET"
    var m = ("" + methodText).toUpperCase()
    return m === "DEL" ? "DELETE" : m
}

function buildKvText(items) {
    var lines = []
    for (var i = 0; i < items.length; i++) {
        var it = items[i]
        if (it.enabled === false) continue
        if (it.key && it.key.length > 0)
            lines.push(it.key + ":" + (it.value || ""))
    }
    return lines.join("\n")
}
```

### 关键约束

`.pragma library` 中的函数：
- ✅ 可以调用彼此
- ✅ 可以是纯 JS：字符串、数组、对象操作
- ❌ 不能访问 QML 对象（`root`、`apiTestVm`、QML 元素 ID）
- ❌ 不能使用 `Theme.token()`
- ❌ 不能修改传入的对象（但可以创建新对象返回）

### 判断函数是否能移到 .pragma library

```qml
// ✅ 能移——纯输入→输出
function normalizeMethod(methodText) { return ... }

// ✅ 能移——只操作参数
function nodeByIdInTree(tree, nodeId) { return ... }

// ❌ 不能移——读取 QML 上下文
function currentTabId() { return root.endpointTabs[root.currentEndpointTab].id }

// ❌ 不能移——调用 apiTestVm
function replaceCollectionTree(tree) { apiTestVm.saveCollectionTree(root.collectionTree) }
```

### 使用

```qml
import "api_utils.js" as ApiUtils

// 调用
var m = ApiUtils.normalizeMethod("DEL")  // "DELETE"
var text = ApiUtils.buildKvText(rows)
```

**效果**：从 QML 中移出 39 个纯函数（464 行）。

---

## 15.6 模式 4 + 5：业务逻辑和数据状态 → ViewModel

### 什么需要移

| 原来的 QML 写法 | 移到 ViewModel |
|----------------|---------------|
| `property var queryParams: [...]` | `@Property("QVariantList") queryParams` |
| `function sendCurrent() { /* 30 行 */ }` | `@Slot("QVariantMap") def sendRequest(self, data)` |
| `function persistCurrentTabDraft() { /* 30 行 */ }` | `@Slot() def persistCurrentTabDraft(self)` |
| `function updateSectionRowKey(s, i, k) { ... }` | `@Slot(str, int, str) def editSectionRowKey(self, s, i, k)` |

### QML 胶水函数的新写法

```qml
// 原来：30 行逻辑在 QML
function sendCurrent() {
    root.saveBodyToMode()
    persistCurrentTabDraft()
    if (root.requestSending) return
    root.requestSending = true
    var mergedHeaders = ApiUtils.buildHeaderText(headersRows)
    if (!currentBodyModeIndexIsFile(...)) { /* 5 行 */ }
    var cookieLine = ApiUtils.buildCookieText(cookieRows).trim()
    if (cookieLine.length > 0) { /* 4 行 */ }
    if (currentBodyModeIndexIsFile(...)) { apiTestVm.sendApiFile(...) }
    else { apiTestVm.sendApi(...) }
}

// 现在：数据组装在 QML，逻辑在 Python
function sendCurrent() {
    apiTestVm.sendRequest({
        method: requestActionBar.getMethodText(),
        url: requestActionBar.getUrlText(),
        paramsText: ApiUtils.buildKvText(apiTestVm.pathParams) + "\n" +
                    ApiUtils.buildKvText(apiTestVm.queryParams),
        headersText: ApiUtils.buildHeaderText(apiTestVm.headersRows),
        bodyText: bodyTextForRequest(),
        // ... 纯数据组装
    })
}
```

**效果**：根文件从 2903 行降到 508 行（-82%），所有业务逻辑在 Python 中可测试。

---

## 15.7 组件通信方式选择

| 组件类型 | 通信方式 | 例子 |
|---------|---------|------|
| 通用 UI 组件 | property 下传 + signal 上抛 | `KvTableSection` |
| 业务组件（不复用） | 直接访问 `apiTestVm` 和 `root.xxx` | `ApiBodyTab` |
| 函数引用传递 | `property var methodColorFn: null` | `ApiEndpointTabsBar` |

```qml
// 方式 1: property + signal（通用组件）
KvTableSection {
    rows: apiTestVm.queryParams
    onRowKeyCommitted: (i, k) => apiTestVm.editSectionRowKey("query", i, k)
}

// 方式 2: 直接访问 ViewModel（业务组件）
ApiBodyTab {
    bodyModes: apiTestVm.bodyModes     // 属性下传
    currentBodyMode: apiTestVm.currentBodyMode
    onBodyModeClicked: index => apiTestVm.setCurrentBodyMode(index)
}

// 方式 3: 函数引用传递
ApiEndpointTabsBar {
    methodColorFn: root.methodColor    // 传递本地函数
    envTagFn: ApiUtils.envTag          // 传递工具函数
}
```

---

## 15.8 文件组织规范

```
src/features/my_plugin/
├── plugin.json
├── runtime.py
├── view_model.py              // 所有业务逻辑
├── service.py                 // 纯业务 Service
├── MyPage.qml                 // 主页面（< 200 行为佳）
├── api_utils.js               // 纯函数库（可选）
└── components/                // 子组件
    ├── MyTableSection.qml     // 可复用组件
    ├── MyDetailPanel.qml      // 功能面板
    └── MySettingsTab.qml      // 选项卡
```

```text
src/app/ui/                    // 跨插件通用组件
├── UiButton.qml
├── UiTextField.qml
├── UiTextArea.qml
├── UiSwitch.qml
├── UiComboBox.qml
├── UiCheckBox.qml
└── UiIcon.qml
```

---

## 15.9 api_test 拆分全景

```
拆分前：ApiTestPage.qml (2903 行)
  ├── 40 个 root 属性
  ├── 80 个 JS 函数（~1400 行）
  └── 视觉树（~1450 行）
        ├── 端点 Tab 栏（260 行内联）
        ├── 9 个 StackLayout Tab（600 行内联）
        ├── 响应面板（250 行内联）
        └── 5 个 Popup/Dialog（60 行）

拆分后：
  ApiTestPage.qml (508 行)          ← 纯 View
  api_utils.js (464 行)             ← 纯函数
  view_model.py (969 行)            ← 全部业务逻辑
  components/
    ├── KvTableSection.qml (98)     ← 可复用 K-V 表
    ├── ApiBodyTab.qml (214)        ← Body 编辑 Tab
    ├── ApiAuthTab.qml (79)         ← 认证 Tab
    ├── ApiSettingsTab.qml (105)    ← 设置 Tab
    ├── ApiResponsePanel.qml (289)  ← 响应面板
    ├── ApiEndpointTabsBar.qml (223)← 端点 Tab 栏
    ├── ApiKvRow.qml (174)          ← K-V 行（已有）
    ├── ApiKvTableHeader.qml (79)   ← 表头（已有）
    ├── ApiCollectionSidebar.qml    ← 侧边栏（已有）
    ├── ApiRequestActionBar.qml     ← 请求栏（已有）
    ├── ApiRequestTabsBar.qml       ← 子 Tab 栏（已有）
    ├── ApiEnvPopup.qml             ← 环境选择（已有）
    ├── ApiTabActionsPopup.qml      ← Tab 菜单（已有）
    ├── ApiMagicValuePanel.qml      ← 魔法值（已有）
    ├── ApiTypeSelector.qml         ← 类型选择（已有）
    └── ApiDeleteButton.qml         ← 删除按钮（已有）
```

---

## 15.10 实战练习

1. 在 api_test 中找一个还能拆的块（30-50 行），抽成一个新组件
2. 检查新组件：是否有硬编码的 `root.xxx` 引用？如果有，改成 property 传递
3. 验证 QML 能独立加载：`QQmlComponent(engine, QUrl.fromLocalFile("yourComponent.qml"))`
4. 看看 `EnvManagerDialog.qml`，思考为什么它在 `api_test/` 而不在 `components/`？

---

[上一章：主题系统](14-theme-system.zh-CN.md) | [下一章：全局热键](16-hotkeys.zh-CN.md)

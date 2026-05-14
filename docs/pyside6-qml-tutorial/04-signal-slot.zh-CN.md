# 第 4 章：QML 与 Python 通信（上）——Signal 和 Slot

本章用本项目真实代码，详解 PySide6 中 QML 和 Python 的双向通信机制。

---

## 4.1 核心概念

PySide6 中，要让 QML 和 Python 通信，Python 类必须继承 `QObject`：

```python
from PySide6.QtCore import QObject, Signal, Slot

class LauncherBridge(QObject):  # 继承 QObject 是关键
    ...
```

三个核心机制：

| 机制 | 方向 | 作用 |
|------|------|------|
| `Signal` | Python → QML | 通知 QML "数据变了" |
| `@Property` | Python → QML（读），QML → Python（写） | 暴露数据给 QML |
| `@Slot` | QML → Python | QML 可以调用的方法 |

> **新手口诀：Signal 是 Python 往外发通知，Property 是数据挂载点，Slot 是 QML 可以按的方法按钮。**

---

## 4.2 注入 Python 对象到 QML

文件：`src/app/main.py`

```python
engine = QQmlApplicationEngine()

# 关键：获取根上下文
ctx = engine.rootContext()

# 注入 Python 对象
bridge = LauncherBridge(command_service, plugin_context.services)
ctx.setContextProperty("launcherBridge", bridge)
ctx.setContextProperty("app", app_vm)
```

之后在**任意 QML 文件**中都可以直接访问：

```qml
// 全局可用，不需要 import
launcherBridge.performSearch("hello")
app.theme
```

---

## 4.3 Signal：Python 通知 QML

### 定义

```python
class LauncherBridge(QObject):
    # 无参数信号
    searchCompleted = Signal()

    # 带参数信号
    pluginLaunched = Signal(str)
    pluginCommandLaunched = Signal(str, str, str, "QVariantMap")

    # 复杂类型用字符串声明
    pluginClosed = Signal(str)
```

### 触发

```python
def performSearch(self, query: str) -> None:
    self._results = self._command_service.search(query, context)
    self.searchCompleted.emit()  # 发出信号！
```

### QML 接收信号

**方式 1：Signal 触发属性刷新**

```python
@Property("QVariantList", notify=searchCompleted)
def searchResults(self) -> list[dict]:
    return self._results
```

```qml
ListView {
    model: launcherBridge.searchResults  // 自动刷新
}
```

**方式 2：QML 直接连接信号处理函数**

在 `main.py` 中：
```python
bridge.pluginClosed.connect(session_mgr.close_plugin)
bridge.pluginInputEdited.connect(on_plugin_input_edited)
```

**方式 3：QML `Connections` 块**

```qml
Connections {
    target: apiTestVm
    function onApiResponseReady(title, bodyText, details) {
        // Python 发出 apiResponseReady.emit(title, body, details)
        // QML 自动调用 onApiResponseReady，参数自动对应
        responsePanel.detailTab = 0
    }
}
```

**命名规则**：Python 信号 `mySignal` → QML 处理函数 `onMySignal`（首字母大写 + `on` 前缀）。

---

## 4.4 @Slot：QML 调用 Python

### 定义

```python
class LauncherBridge(QObject):
    @Slot(str)                          # QML 传一个字符串
    def performSearch(self, query: str) -> None:
        ...

    @Slot(str, str)                     # QML 传两个字符串
    def launchItem(self, item_id: str, source: str) -> None:
        ...

    @Slot(str, str, str)                # 三个参数
    def launchItemWithInput(self, item_id: str, source: str, input_text: str) -> None:
        ...

    @Slot(str, result=str)              # 有返回值
    def getValue(self, key: str) -> str:
        return self._data.get(key, "")

    @Slot()                             # 无参数
    def hideLauncher(self) -> None:
        self.hideLauncherRequested.emit()
```

### QML 调用

```qml
// 在 TextField.onTextChanged 中调用
launcherBridge.performSearch(text)

// 点击按钮时调用
launcherBridge.launchItem(itemId, "plugin")

// 调用有返回值的方法
var result = apiTestVm.createCollectionNode(parentId, kind, name, "GET", "/new")
```

---

## 4.5 完整数据流案例：启动器搜索

```text
用户输入 "json"
  │
  ▼ QML
TextField.onTextChanged
  → launcherBridge.performSearch("json")
  │
  ▼ Python (@Slot)
LauncherBridge.performSearch("json")
  → CommandService.search("json", context)
  → self._results = [...]
  │
  ▼ Python (Signal)
self.searchCompleted.emit()
  │
  ▼ QML
ListView 绑定到 searchResults（标记了 notify=searchCompleted）
  → ListView 重新渲染，显示搜索结果
```

---

## 4.6 QML 调 Python 的三种方式

```qml
// 1. 直接调 Slot
launcherBridge.performSearch(text)

// 2. 读写 Property
apiTestVm.currentEndpointTab = 0        // 设置
var tab = apiTestVm.currentEndpointTab  // 读取

// 3. 绑定表达式（自动跟踪变化）
text: apiTestVm.currentEndpointTab >= 0 ? "有标签页" : "无标签页"
color: apiTestVm.requestSending ? "gray" : "blue"
```

---

## 4.7 launcher_bridge.py 完整解读

```python
class LauncherBridge(QObject):
    # === Signals ===
    searchCompleted = Signal()                          # 搜索完成
    pluginLaunched = Signal(str)                        # 插件被启动
    pluginCommandLaunched = Signal(str, str, str, "QVariantMap")  # 完整参数
    pluginClosed = Signal(str)                          # 插件被关闭
    restartRequested = Signal()                         # 请求重启
    hideLauncherRequested = Signal()                    # 请求隐藏启动器

    # === Properties ===
    @Property("QVariantList", notify=searchCompleted)
    def searchResults(self) -> list[dict]:
        return self._results

    @Property(str, notify=pluginInputChanged)
    def pluginInput(self) -> str:
        return self._plugin_input

    # === Slots ===
    @Slot(str)
    def performSearch(self, query: str) -> None: ...

    @Slot(str, str)
    def launchItem(self, item_id: str, source: str) -> None: ...

    @Slot(str)
    def closePlugin(self, plugin_id: str) -> None: ...

    @Slot()
    def hideLauncher(self) -> None: ...
```

---

## 4.8 实战练习

1. 在 `app_view_model.py` 中加一个 `@Property(str)` 属性 `greeting`，值为 `"Hello from Python"`
2. 在 `LauncherWindow.qml` 中加一个 `Text { text: app.greeting }` 验证
3. 在 `app_view_model.py` 中加一个 `@Slot(str)` 方法 `setGreeting(name)`，从 QML 按钮调用它
4. 运行 `uv run app` 验证

---

[下一章：QML 与 Python 通信（下）——Property 和数据绑定](05-property-binding.zh-CN.md)

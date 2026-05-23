# 第 8 章：插件系统（上）——Manifest 与懒加载

本章拆解项目插件系统的核心机制：Manifest 声明、发现与解析、Runtime 懒加载。

---

## 8.1 插件系统的设计目标

```
1. 应用启动时不加载任何插件代码（只读 JSON 清单）
2. 插件声明自己的命令、关键词、前缀、推荐规则
3. 框架不感知插件业务（没有 if plugin_id == "xxx"）
4. 用户启动插件时才创建 ViewModel，关闭时完整清理
```

---

## 8.2 从 plugin.json 到 PluginManifest

### plugin.json 示例

```json
{
  "id": "json-parser",
  "name": "JSON 解析",
  "entrypoint": "runtime:create_runtime",
  "qmlPage": "JsonParserPage.qml",
  "contextProperty": "jsonParserVm",
  "commands": [
    {
      "id": "json-parser.open",
      "title": "JSON 解析",
      "launchMode": "inline_view",
      "keywords": ["json", "格式化"],
      "prefixes": ["json", "jq"],
      "matchers": [
        {"source": "input", "kind": "json", "boost": 180}
      ]
    }
  ]
}
```

### 解析为 Python 数据类

文件：`src/app/plugins/manifest.py`

```python
@dataclass(frozen=True, slots=True)
class PluginManifest:
    id: str
    name: str
    version: str
    description: str
    icon: str
    entrypoint: str
    qml_page: str
    context_property: str = ""
    activation: str = "lazy"
    commands: list[CommandContribution] = field(default_factory=list)
    package_dir: Path | None = None  # 插件所在目录

@dataclass(frozen=True, slots=True)
class CommandContribution:
    id: str
    title: str
    subtitle: str = ""
    keywords: list[str] = field(default_factory=list)
    prefixes: list[str] = field(default_factory=list)
    launch_mode: str = "inline_view"
    matchers: list[ContextMatcher] = field(default_factory=list)
```

关键设计：
- `@dataclass(frozen=True)` — **不可变对象**，保证线程安全
- `slots=True` — 节省内存（100 个插件也只占几 KB）
- `package_dir` — 标记插件物理位置，加载 QML 和执行 Runtime import 时使用

---

## 8.3 清单发现与扫描

文件：`src/app/plugins/manifest_loader.py`

```python
def load_all_plugin_manifests() -> list[PluginManifest]:
    return merge_manifests(
        load_bundled_manifests(),      # src/features/*/plugin.json
        load_external_manifests(),     # plugins/*/plugin.json
    )
```

### 扫描逻辑

```python
def discover_manifest_files(plugin_root: Path) -> list[Path]:
    candidates: set[Path] = set()
    # 扫描根目录下的 plugin.json 和 *.plugin.json
    for pattern in ("plugin.json", "*.plugin.json"):
        candidates.update(plugin_root.glob(pattern))
    # 扫描子目录（每个子目录是一个插件包）
    for child in plugin_root.iterdir():
        if child.is_dir():
            for pattern in ("plugin.json", "*.plugin.json"):
                candidates.update(child.glob(pattern))
    return sorted(candidates)
```

### 路径解析

```python
def load_manifest_file(manifest_path: Path) -> PluginManifest:
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    package_dir = manifest_path.parent.resolve()

    return PluginManifest(
        id=raw["id"],
        entrypoint=raw["entrypoint"],
        qml_page=_resolve_plugin_path(raw.get("qmlPage"), package_dir),
        package_dir=package_dir,
        ...
    )

def _resolve_plugin_path(value: str, package_dir: Path) -> str:
    """把相对路径 qmlPage 解析为 file:// URL"""
    if "://" in value or Path(value).is_absolute():
        return value
    return (package_dir / value).resolve().as_uri()
```

例如 `"qmlPage": "JsonParserPage.qml"` 解析为：
```
file:///D:/project/src/features/json_parser/JsonParserPage.qml
```

---

## 8.4 Runtime 懒加载——核心流程

### 关键原则：读 Manifest ≠ 加载 Runtime

```
应用启动
  │
  ├─ load_all_plugin_manifests()
  │    └─ 只读 JSON，创建 PluginManifest 数据类
  │    └─ 不 import 任何插件 Python 代码
  │    └─ 不创建 ViewModel
  │    └─ 不加载 QML
  │
  └─ PluginManager(manifests)
       └─ 持有所有 Manifest 引用，等待启动请求
```

### 用户搜索并启动插件时

```
QML: launchPlugin("json-parser")
  → LauncherBridge.launchPlugin("json-parser")
  → pluginCommandLaunched.emit(...)
  → main.py: on_plugin_launched(...)
  → session_mgr.open_plugin("json-parser", ...)
  → plugin_manager.open_session(...)
  → plugin_manager._load_runtime(manifest)        ← 现在才 import！
```

### _load_runtime 内部实现

```python
def _load_runtime(self, manifest: PluginManifest) -> PluginRuntime:
    # 1. 如果已加载，直接返回
    runtime = self._runtimes.get(manifest.id)
    if runtime is not None:
        return runtime

    # 2. 解析 entrypoint: "runtime:create_runtime"
    #    → module_name="runtime", factory_name="create_runtime"
    module_name, factory_name = self._parse_entrypoint(manifest)

    # 3. 动态 import 插件模块
    module = self._import_module(manifest, module_name)

    # 4. 调用工厂函数
    factory: RuntimeFactory = getattr(module, factory_name)
    runtime = factory()                          # ← 插件代码开始执行

    # 5. 缓存
    self._runtimes[manifest.id] = runtime
    return runtime
```

### _import_module —— 关键实现

```python
@staticmethod
def _import_module(manifest: PluginManifest, module_name: str):
    package_dir = manifest.package_dir
    module_path = (Path(package_dir) / module_name).with_suffix(".py")

    # 创建合成 Python 包（让插件内的相对 import 正常工作）
    package_name = f"_py_desktop_plugin_{safe_name}"
    _ensure_plugin_packages(package_name, package_dir, module_name)

    # 从文件位置加载模块
    spec = importlib.util.spec_from_file_location(full_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module
```

---

## 8.5 entrypoint 格式

```json
"entrypoint": "runtime:create_runtime"
```

格式：`模块名:函数名`

- `runtime` → 插件目录下的 `runtime.py`
- `create_runtime` → 该模块中的工厂函数

### 最小 Runtime

```python
# runtime.py
from app.plugins.runtime import SimpleQmlRuntime
from .view_model import MyViewModel

def create_runtime():
    return SimpleQmlRuntime(lambda _ctx: MyViewModel())
```

### 自定义 Runtime

```python
class MyRuntime:
    def on_enter(self, ctx, action):
        return QmlPluginSession(action.manifest, "inline_view", MyViewModel())

    def on_exit(self):
        pass

def create_runtime():
    return MyRuntime()
```

---

## 8.6 插件目录与 Manifest

框架支持一个目录放多个 Manifest 文件并共享 Runtime 代码。当前自带插件优先保持一个插件一个目录，目录名使用插件 id 的 snake_case 形式：

```
src/features/system_settings/
├── plugin.json                    # id: "system-settings"
├── runtime.py
├── SystemSettingsPage.qml
└── view_model.py

src/features/about/
├── plugin.json                    # id: "about"
├── runtime.py
└── AboutPage.qml
```

```python
# runtime.py
def create_runtime():
    return SimpleQmlRuntime(lambda _ctx: SystemSettingsViewModel())
```

---

## 8.7 实战练习

1. 查看 `src/features/json_parser/plugin.json` 和 `src/features/clipboard/plugin.json`，对比区别
2. 跟踪 `load_all_plugin_manifests()` 的执行路径
3. 在 `_load_runtime()` 中加 `print()`，验证非后台插件只在启动时才 import
4. 尝试理解合成包机制（`_ensure_plugin_packages`）如何让插件内 `from .view_model import ...` 正常工作

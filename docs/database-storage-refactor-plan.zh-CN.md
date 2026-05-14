# 数据库存储能力封装改造文档

## 背景

当前项目里数据库使用比较分散，主要问题是：

- 多个模块直接 `import sqlite3`，各自调用 `sqlite3.connect(...)`。
- 数据目录路径有的走 `app.paths.db_path()`，有的手动拼 `data/xxx.db` 或插件本地路径。
- SQLite 连接参数不统一，例如 `foreign_keys`、`journal_mode=WAL`、`row_factory`、`check_same_thread`、提交/回滚策略都散落在业务代码里。
- 一些简单配置类数据也放进 SQLite，例如剪贴板设置 `clipboard_settings`，这类数据没有查询关系，不应该为了简单字典读写经过 SQL。
- 插件未来新增持久化时缺少统一入口，容易继续复制旧模式。

本次改造目标是把“存储能力”收敛到内核层，对外提供统一接口：

- 复杂结构、历史记录、索引、需要查询的数据继续使用 SQLite。
- 简单设置、偏好、插件轻量状态使用 JSON 字典存储，不经过 SQL。
- 业务仓库仍然保留 SQL 语义，先不引入 ORM。

## 总体目标

新增 `app.storage` 模块，提供两类能力：

1. `SQLiteDatabase`

   统一封装 SQLite 数据库路径、连接参数、事务上下文和基础 PRAGMA。

2. `JsonDictStore`

   提供轻量字典存储，底层为 JSON 文件，适合简单配置。

插件和内核通过 `StorageManager` 获取存储对象：

```python
from app.storage import StorageManager

storage = StorageManager()
api_db = storage.database("api_test.db")
settings = storage.dict_store("clipboard/settings", defaults={...})
```

插件运行时优先从 `PluginContext.services["storage"]` 取统一存储入口：

```python
storage = ctx.services.get("storage")
```

如果没有，则临时创建 `StorageManager()` 作为兼容兜底。

## 建议新增文件

新增目录：

```text
src/app/storage/
  __init__.py
  sqlite.py
  dict_store.py
  manager.py
```

### `src/app/storage/sqlite.py`

职责：

- 封装 SQLite 路径创建。
- 统一连接参数。
- 统一 `foreign_keys`、`WAL` 等 PRAGMA。
- 提供自动提交、异常回滚、关闭连接的上下文。

建议接口：

```python
SQLiteConnection = sqlite3.Connection
SQLiteRow = sqlite3.Row


class SQLiteDatabase:
    def __init__(
        self,
        path: Path,
        *,
        foreign_keys: bool = True,
        wal: bool = False,
        row_factory=None,
        check_same_thread: bool = True,
        timeout: float = 30.0,
    ) -> None:
        ...

    def open(self, *, row_factory=None, check_same_thread: bool | None = None) -> sqlite3.Connection:
        ...

    @contextmanager
    def connection(self, *, row_factory=None) -> Iterator[sqlite3.Connection]:
        ...
```

实现要点：

- `path.parent.mkdir(parents=True, exist_ok=True)` 放在构造阶段。
- `open()` 内部调用 `sqlite3.connect(str(self.path), ...)`。
- `foreign_keys=True` 时执行 `PRAGMA foreign_keys = ON`。
- `wal=True` 时执行 `PRAGMA journal_mode=WAL`。
- `connection()` 中 `yield conn` 后 `commit()`，异常时 `rollback()`，最后 `close()`。

### `src/app/storage/dict_store.py`

职责：

- 提供 JSON 文件字典存储。
- 适合简单设置、偏好、插件状态，不走 SQL。
- 支持默认值、原子写入、基础 dict 操作。

建议接口：

```python
class JsonDictStore:
    def __init__(self, path: Path, defaults: dict[str, Any] | None = None) -> None:
        ...

    @property
    def loaded_from_existing_file(self) -> bool:
        ...

    def get(self, key: str, default: Any = None) -> Any:
        ...

    def set(self, key: str, value: Any) -> None:
        ...

    def set_many(self, values: dict[str, Any]) -> None:
        ...

    def delete(self, key: str) -> None:
        ...

    def clear(self) -> None:
        ...

    def replace(self, values: dict[str, Any]) -> None:
        ...

    def all(self) -> dict[str, Any]:
        ...

    def items(self) -> list[tuple[str, Any]]:
        ...
```

实现要点：

- 文件不存在时从 `{}` 开始。
- JSON 内容不是 dict 或解析失败时回退 `{}`，不让应用崩溃。
- 写入时先写 `.tmp`，再 `replace()` 到正式文件。
- 使用 `RLock` 保证同进程多处访问时基本安全。
- `loaded_from_existing_file` 用于迁移：如果 JSON 设置文件已存在，则不要再从旧 SQLite 设置表覆盖它。

### `src/app/storage/manager.py`

职责：

- 持有统一数据根目录。
- 根据相对名称生成 SQLite 路径或 JSON 字典路径。
- 对外提供兼容工厂函数。

建议接口：

```python
class StorageManager:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or data_dir()

    def database(self, name: str | Path, **kwargs) -> SQLiteDatabase:
        ...

    def dict_store(self, namespace: str | Path, defaults: dict | None = None) -> JsonDictStore:
        ...

    def path(self, name: str | Path) -> Path:
        ...
```

路径约定：

- SQLite 默认仍在 `data_dir()` 根下，例如 `api_test.db`、`clipboard.db`。
- 字典存储放在 `data_dir() / "stores"` 下，例如：

```text
stores/
  clipboard/
    settings.json
  plugins/
    foo.json
```

命名空间需要做简单安全化，避免非法路径字符：

```python
def _safe_part(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value.strip())
    return text.strip("._") or "default"
```

### `src/app/storage/__init__.py`

统一导出：

```python
from .dict_store import JsonDictStore
from .manager import StorageManager, dict_store, sqlite_database, storage_manager
from .sqlite import SQLiteConnection, SQLiteDatabase, SQLiteRow
```

## 主程序接入

修改 `src/app/main.py`：

1. 导入：

```python
from .storage import StorageManager
```

2. 初始化平台服务后创建：

```python
storage = StorageManager()
```

3. 注入 `PluginContext.services`：

```python
plugin_context = PluginContext(
    command_index=command_index,
    dynamic_commands=dynamic_commands,
    platform=platform_api,
    services={
        "platform": platform_api,
        "storage": storage,
    },
)
```

注意：

- 不需要把 `StorageManager` 加到 QML context。
- 插件通过 Python runtime 的 `PluginContext` 使用即可。

## 核心命令索引迁移

文件：`src/app/commands/command_index_db.py`

目标：

- 去掉直接 `sqlite3.connect`。
- 构造函数接受 `SQLiteDatabase | Path | None`。
- 兼容旧调用 `CommandIndexDb(db_path=Path(...))`。

建议签名：

```python
class CommandIndexDb:
    def __init__(
        self,
        database: SQLiteDatabase | Path | None = None,
        *,
        db_path: Path | None = None,
    ) -> None:
        if database is None and db_path is not None:
            database = db_path
        if isinstance(database, SQLiteDatabase):
            self._database = database
        else:
            self._database = sqlite_database(
                database or "command_index.db",
                wal=True,
                check_same_thread=False,
            )
        self._db_path = self._database.path
        self._icon_dir = self._db_path.parent / "app_icons"
        self._db = self._database.open(check_same_thread=False)
```

保留现有业务行为：

- `command_usage` 表不变。
- `app_entries` 表不变。
- `sync_apps()`、`search_apps()`、`record_launch()` 行为不变。
- `close()` 仍然关闭长期连接。

## API 测试插件迁移

涉及文件：

```text
src/features/api_test/db.py
src/features/api_test/service.py
src/features/api_test/repositories/collection_repo.py
src/features/api_test/repositories/environment_repo.py
src/features/api_test/repositories/tab_repo.py
src/features/api_test/variable_service.py
src/features/api_test/ws_service.py
src/features/api_test/case_service.py
```

### `db.py`

目标：

- `ApiDatabase` 持有 `SQLiteDatabase`。
- `connect()` 仍保留，作为兼容入口。
- `ensure_schema()` 改用 `self._database.connection()`，保证提交和关闭。
- 兼容旧参数 `path=...`。

建议：

```python
class ApiDatabase:
    def __init__(
        self,
        database: SQLiteDatabase | Path | None = None,
        *,
        path: Path | None = None,
    ) -> None:
        if database is None and path is not None:
            database = path
        if isinstance(database, SQLiteDatabase):
            self._database = database
        else:
            self._database = sqlite_database(database or "api_test.db")
        self.path = self._database.path
        self.ensure_schema()

    @property
    def storage(self) -> SQLiteDatabase:
        return self._database

    def connect(self) -> SQLiteConnection:
        return self._database.open()
```

### 各 Repository / Service

目标：

- 构造参数从 `db_path` 迁移到 `SQLiteDatabase | Path | str`。
- 内部保存 `self._database`。
- 所有短连接读写改成 `with self._database.connection() as conn:`。
- 保留 `self._db_path = self._database.path`，降低迁移风险。

示例：

```python
class TabRepository:
    def __init__(self, database: SQLiteDatabase | Path) -> None:
        self._database = database if isinstance(database, SQLiteDatabase) else sqlite_database(database)
        self._db_path = self._database.path

    def list_tabs(self) -> list[dict]:
        with self._database.connection() as conn:
            rows = conn.execute(...).fetchall()
```

`service.py` 中共享同一个数据库对象：

```python
self._database = ApiDatabase()
self._collections = CollectionRepository(self._database.storage)
self._environments = EnvironmentRepository(self._database.storage)
self._tabs = TabRepository(self._database.storage)
self._variables = VariableService(self._database.storage)
self._ws = WebSocketSessionService(self._database.storage, self._variables)
self._cases = DebugCaseService(self._database.storage)
```

不要改变：

- 表结构。
- API 调试数据格式。
- `SCHEMA_VERSION` 行为。
- QML / ViewModel 对外接口。

## 剪贴板插件迁移

涉及文件：

```text
src/features/clipboard/runtime.py
src/features/clipboard/service.py
```

目标：

- 剪贴板历史仍用 SQLite：`clipboard.db`。
- 剪贴板设置迁移到 JSON 字典：`stores/clipboard/settings.json`。
- 旧 SQLite 表 `clipboard_settings` 只读迁移，不强制删除。

### `runtime.py`

从 `PluginContext.services["storage"]` 获取统一入口：

```python
storage = ctx.services.get("storage")
if not isinstance(storage, StorageManager):
    storage = StorageManager()
    ctx.services["storage"] = storage

self._service = ClipboardBackgroundService(
    storage.database(
        "clipboard.db",
        check_same_thread=False,
    ),
    settings_store=storage.dict_store(
        "clipboard/settings",
        defaults=DEFAULT_CLIPBOARD_CONFIG,
    ),
)
```

### `service.py`

`ClipboardHistoryStore` 建议签名：

```python
class ClipboardHistoryStore(QObject):
    def __init__(
        self,
        database: SQLiteDatabase | Path,
        settings_store: JsonDictStore | None = None,
    ) -> None:
        ...
```

SQLite 连接：

```python
self._db = self._database.open(row_factory=SQLiteRow, check_same_thread=False)
```

设置读写：

```python
def get_config(self) -> dict:
    config = DEFAULT_CLIPBOARD_CONFIG.copy()
    for key, value in self._settings.items():
        if key in config:
            config[key] = value
    return config

def set_config_value(self, key: str, value: object) -> None:
    if key not in DEFAULT_CLIPBOARD_CONFIG:
        return
    self._settings.set(key, value)
    self.configChanged.emit()
```

旧数据迁移：

```python
def _migrate_settings_from_sqlite(self) -> None:
    if self._settings.loaded_from_existing_file:
        return
    table = self._db.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = 'clipboard_settings'
        """
    ).fetchone()
    if table is None:
        return
    rows = self._db.execute("SELECT key, value FROM clipboard_settings").fetchall()
    values = {}
    for row in rows:
        key = str(row["key"])
        if key not in DEFAULT_CLIPBOARD_CONFIG:
            continue
        try:
            values[key] = json.loads(row["value"])
        except json.JSONDecodeError:
            values[key] = DEFAULT_CLIPBOARD_CONFIG[key]
    if values:
        self._settings.set_many(values)
```

注意：

- `_migrate_settings_from_sqlite` 必须是实例方法，不要加 `@staticmethod`。
- 如果 JSON 文件已经存在，不要从旧 SQLite 表覆盖用户新设置。
- `clipboard_settings` 表可以保留，不影响运行。

## 统一接口使用规则

后续新增持久化时按以下规则选择：

### 使用 SQLite

适合：

- 需要搜索、过滤、排序、分页。
- 有多表关系。
- 历史记录、索引、集合树。
- 数据量可能增长。
- 需要事务一致性。

示例：

```python
storage.database("my_feature.db")
```

### 使用字典存储

适合：

- 插件配置。
- UI 偏好。
- 最近一次选项。
- 简单开关。
- 少量键值状态。

示例：

```python
settings = storage.dict_store(
    "my_feature/settings",
    defaults={"enabled": True, "limit": 100},
)
settings.set("enabled", False)
```

不适合：

- 大量列表数据。
- 需要按字段搜索的数据。
- 频繁高并发写入。
- 需要跨多个键事务一致性的复杂数据。

## 当前工作树可能已有的半成品修改

如果接手时使用的是当前工作树，请先重点检查这些文件：

```text
src/app/storage/__init__.py
src/app/storage/sqlite.py
src/app/storage/dict_store.py
src/app/storage/manager.py
src/app/main.py
src/app/commands/command_index_db.py
src/features/api_test/db.py
src/features/api_test/service.py
src/features/api_test/repositories/collection_repo.py
src/features/api_test/repositories/environment_repo.py
src/features/api_test/repositories/tab_repo.py
src/features/api_test/variable_service.py
src/features/api_test/ws_service.py
src/features/api_test/case_service.py
src/features/clipboard/runtime.py
src/features/clipboard/service.py
```

已发现并需要确保修正的点：

- `ClipboardHistoryStore._migrate_settings_from_sqlite` 不能是静态方法。
- `ApiDatabase.ensure_schema()` 应通过 `self._database.connection()` 执行，避免连接未关闭。
- `CommandIndexDb.__init__` 建议保留 `db_path=` 兼容。
- `ApiDatabase.__init__` 建议保留 `path=` 兼容。
- 所有 API 测试相关类尽量共享同一个 `SQLiteDatabase` 对象。

## 验证清单

由于项目没有配置正式测试命令，建议至少执行以下验证：

### 语法编译

```powershell
uv run python -m compileall src
```

### 存储层 smoke test

可用临时目录验证：

```powershell
$env:PY_DESKTOP_TOOLS_DATA_DIR="C:\tmp\py_desktop_tools_storage_smoke"
uv run python - <<'PY'
from app.storage import StorageManager

s = StorageManager()
db = s.database("smoke.db")
with db.connection() as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO t (name) VALUES (?)", ("ok",))
with db.connection() as conn:
    print(conn.execute("SELECT COUNT(*) FROM t").fetchone()[0])

store = s.dict_store("smoke/settings", defaults={"enabled": True})
store.set("limit", 3)
print(store.all())
PY
```

如果 PowerShell 不方便 heredoc，可改成临时 `.py` 文件或 `python -c`。

### API 测试数据库初始化

```powershell
$env:PY_DESKTOP_TOOLS_DATA_DIR="C:\tmp\py_desktop_tools_api_smoke"
uv run python -c "from features.api_test.service import ApiTestService; s=ApiTestService(); print(len(s.list_environments())); s.close()"
```

预期：

- 不报错。
- 至少有一个默认环境。
- `api_test.db` 出现在临时数据目录。

### 剪贴板设置存储验证

剪贴板服务依赖 QApplication，不建议用纯 Python 直接实例化完整背景服务。可以只验证 `JsonDictStore` 路径：

```powershell
$env:PY_DESKTOP_TOOLS_DATA_DIR="C:\tmp\py_desktop_tools_clipboard_smoke"
uv run python -c "from app.storage import StorageManager; s=StorageManager(); st=s.dict_store('clipboard/settings', defaults={'hotkey':'Alt+V'}); st.set('hotkey','Alt+C'); print(st.get('hotkey')); print(st.path)"
```

预期：

- 输出 `Alt+C`。
- 文件路径位于 `stores/clipboard/settings.json`。

### 应用启动

```powershell
uv run app
```

手动检查：

- 启动无异常。
- Alt+Space 启动器可打开。
- API 测试插件可打开，默认环境存在。
- 剪贴板插件可打开，热键设置可读写。
- 第二次启动后剪贴板设置保持不丢失。

## 回归风险

重点关注：

- 长连接对象：`CommandIndexDb` 和 `ClipboardHistoryStore` 仍然持有长期连接，关闭逻辑不能丢。
- `row_factory`：剪贴板代码使用 `row["name"]` 这种访问方式，必须确保连接设置 `SQLiteRow`。
- `foreign_keys`：API 环境变量/请求头依赖外键级联删除，默认要开启。
- 旧设置迁移：不要在 JSON 设置已存在时用旧 SQLite 数据覆盖。
- 构造函数签名：保留 `db_path=`、`path=` 可以减少外部脚本破坏。

## 完成标准

完成后应满足：

- 除 `src/app/storage/sqlite.py` 外，业务代码不再直接 `import sqlite3`。
- 除迁移读取旧表外，剪贴板设置不再读写 `clipboard_settings`。
- `PluginContext.services` 中存在统一 `"storage"` 服务。
- API 测试、命令索引、剪贴板历史都通过 `SQLiteDatabase` 获取连接。
- 剪贴板设置通过 `JsonDictStore` 读写 JSON 文件。
- `uv run python -m compileall src` 通过。
- `uv run app` 能正常启动。


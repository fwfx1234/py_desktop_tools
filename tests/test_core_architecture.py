from __future__ import annotations

from pathlib import Path
import os
import sys
import tempfile
import unittest
import logging
from types import SimpleNamespace
from threading import Event
from unittest.mock import patch

from PySide6.QtCore import QObject, QPoint


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.commands.command_context import CommandContextMatcher
from app.commands.command_index_db import CommandIndexDb
from app.commands.command_launcher import CommandLauncher
from app.commands.context import build_launcher_context
from app.commands.ranker import CommandRanker
from app.commands.usage_service import CommandUsageService
from app.concurrency import PythonTaskRunner
from app.hotkey_coordinator import HotkeyCoordinator
from app.logging.manager import LoggingManager
from app.platform.models import PlatformResult
from app.platform.services import PlatformServices
from app.plugins.manifest import ContextMatcher
from app.plugins.manifest import CommandContribution, PluginManifest
from app.plugins.session_state import (
    PluginSessionState,
    active_state,
    reactivate_state,
    retained_state,
)
from app.plugin_surface_coordinator import PluginSurfaceCoordinator, PluginWindowSurface
from app.plugins.service_registry import ServiceRegistry
from app.services.clipboard.service import ClipboardService
from app.storage import StorageManager


class CommandRankingTests(unittest.TestCase):
    def test_ranker_matches_title_keyword_and_pinyin_initial(self) -> None:
        self.assertEqual(CommandRanker.score("json", "JSON 解析", ["jq"], "")[0], 90)
        self.assertEqual(CommandRanker.score("jq", "JSON 解析", ["jq"], "")[0], 85)
        self.assertGreaterEqual(CommandRanker.score("j", "JSON 解析", [], "")[0], 70)

    def test_context_matcher_applies_prefix_and_input_reasons(self) -> None:
        context = build_launcher_context("api https://example.com", {"api"})
        score, reasons = CommandContextMatcher.apply_context(
            0,
            context,
            ["api"],
            [ContextMatcher(source="input", kind="url", boost=120)],
        )

        self.assertEqual(score, 360)
        self.assertEqual(reasons, ["prefix:api", "input:url"])
        self.assertEqual(
            CommandContextMatcher.launch_input_policy(0, context, ["api"], reasons),
            ("", "command", True),
        )

    def test_context_matcher_passes_content_for_matcher_launch(self) -> None:
        context = build_launcher_context("https://example.com", {"api"})
        score, reasons = CommandContextMatcher.apply_context(
            0,
            context,
            [],
            [ContextMatcher(source="input", kind="url", boost=120)],
        )

        self.assertEqual(score, 120)
        self.assertEqual(reasons, ["input:url"])
        self.assertEqual(
            CommandContextMatcher.launch_input_policy(0, context, [], reasons),
            ("https://example.com", "content", True),
        )


class StorageTests(unittest.TestCase):
    def test_database_dict_store_persists_namespace_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = StorageManager(Path(tmp))
            settings = storage.dict_store("plugin/settings", defaults={"enabled": True})
            settings["limit"] = 3

            reopened = storage.dict_store("plugin/settings")
            other = storage.dict_store("other/settings", defaults={"limit": 9})

            self.assertTrue(reopened.loaded_from_existing_store)
            self.assertEqual(reopened.get("enabled"), True)
            self.assertEqual(reopened.get("limit"), 3)
            self.assertEqual(other.get("limit"), 9)
            self.assertEqual(settings.path.name, "dict_store.db")


class CommandIndexTests(unittest.TestCase):
    def test_command_index_updates_apps_without_dropping_existing_icon(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = CommandIndexDb(StorageManager(Path(tmp)).database("command_index.db"))
            try:
                db.sync_apps(
                    [
                        {
                            "platform": "windows",
                            "name": "Foo App",
                            "launch_path": "foo.lnk",
                            "bundle_id": "",
                            "icon_path": "old.png",
                        }
                    ]
                )
                db.sync_apps(
                    [
                        {
                            "platform": "windows",
                            "name": "Foo App",
                            "launch_path": "foo.lnk",
                            "bundle_id": "",
                            "icon_path": "",
                        }
                    ]
                )

                self.assertEqual(db.search_apps("Foo")[0]["iconPath"], "old.png")

                db.record_launch("plugin:foo")
                db.record_launch("plugin:foo")
                self.assertEqual(db.usage_map()["plugin:foo"][0], 2)
            finally:
                db.close()


class CommandUsageServiceTests(unittest.TestCase):
    def test_usage_recording_is_best_effort(self) -> None:
        class BrokenIndex:
            def usage_map(self):
                raise OSError("disk I/O error")

            def record_launch(self, key: str) -> None:
                raise OSError(f"disk I/O error: {key}")

        service = CommandUsageService(BrokenIndex())  # type: ignore[arg-type]

        self.assertEqual(service.usage_map(), {})
        service.record_plugin_launch("json-parser")
        service.record_item_launch({"usageKey": "plugin:json-parser"})

    def test_external_launch_ignores_usage_record_failure(self) -> None:
        class BrokenIndex:
            def record_launch(self, key: str) -> None:
                raise OSError(f"disk I/O error: {key}")

        class Result:
            ok = True
            code = ""
            message = ""

        class ExternalLauncher:
            def launch_system_action(self, action: str) -> Result:
                self.action = action
                return Result()

            def launch_app(self, app: dict) -> Result:
                self.app = app
                return Result()

        class Platform:
            external_launcher = ExternalLauncher()

        launcher = CommandLauncher(BrokenIndex(), Platform())  # type: ignore[arg-type]

        self.assertEqual(
            launcher.launch_external_item("system:lock-screen", "system", {"action": "lock", "name": "Lock"}),
            "Lock",
        )
        self.assertEqual(
            launcher.launch_external_item("app:demo", "app", {"launchPath": "demo.lnk", "name": "Demo"}),
            "Demo",
        )


class ServiceRegistryTests(unittest.TestCase):
    def test_registry_exposes_typed_core_services(self) -> None:
        registry = ServiceRegistry()
        platform = object()
        storage = object()
        clipboard = object()

        registry.platform = platform
        registry.storage = storage
        registry.clipboard = clipboard

        self.assertIs(registry.require_platform(), platform)
        self.assertIs(registry.require_storage(), storage)
        self.assertIs(registry.clipboard, clipboard)
        self.assertIs(registry.get_typed("storage", object), storage)

        registry.platform = None
        with self.assertRaises(RuntimeError):
            registry.require_platform()


class PluginSessionStateTests(unittest.TestCase):
    def test_session_state_helpers_make_host_transitions_explicit(self) -> None:
        self.assertEqual(active_state("inline_view"), PluginSessionState.ACTIVE_INLINE)
        self.assertEqual(active_state("list"), PluginSessionState.ACTIVE_LIST)
        self.assertEqual(active_state("window"), PluginSessionState.ACTIVE_WINDOW)
        self.assertEqual(active_state("inline_view", "window"), PluginSessionState.ACTIVE_WINDOW)

        retained = retained_state("inline_view", "inline")
        self.assertEqual(retained, PluginSessionState.RETAINED_INLINE)
        self.assertTrue(retained.retained)
        self.assertEqual(retained.host, "inline")

        self.assertEqual(
            reactivate_state(PluginSessionState.RETAINED_WINDOW, "inline_view"),
            PluginSessionState.ACTIVE_WINDOW,
        )


class PluginSurfaceCoordinatorTests(unittest.TestCase):
    def test_window_config_preserves_always_on_top_option(self) -> None:
        from app.plugin_surface_coordinator import _plugin_window_config

        manifest = PluginManifest(
            id="clipboard",
            name="Clipboard",
            version="1",
            description="",
            icon="",
            entrypoint="runtime:create_runtime",
            qml_page="ClipboardWindowPage.qml",
            window_options={"width": 980, "height": 640, "alwaysOnTop": True},
        )
        session = SimpleNamespace(manifest=manifest)

        config = _plugin_window_config(session)

        self.assertEqual(config["width"], 980)
        self.assertEqual(config["height"], 640)
        self.assertTrue(config["alwaysOnTop"])

    def test_stale_window_destroy_does_not_forget_new_surface(self) -> None:
        coordinator = PluginSurfaceCoordinator.__new__(PluginSurfaceCoordinator)
        old_window = object()
        new_window = object()
        coordinator._windows = {
            "clipboard": PluginWindowSurface(plugin_id="clipboard", window=new_window)
        }

        coordinator._forget_window_surface("clipboard", old_window)

        self.assertIs(coordinator._windows["clipboard"].window, new_window)

        coordinator._forget_window_surface("clipboard", new_window)

        self.assertNotIn("clipboard", coordinator._windows)

    def test_duplicate_window_open_is_ignored_while_create_is_in_progress(self) -> None:
        coordinator = PluginSurfaceCoordinator.__new__(PluginSurfaceCoordinator)
        coordinator._windows = {}
        coordinator._opening_windows = {"clipboard"}
        coordinator._qt_app = SimpleNamespace(topLevelWindows=lambda: [])
        opened: list[str] = []
        coordinator._open_independent_window = lambda plugin_id, session: opened.append(plugin_id) or True

        shown = coordinator._show_window_surface("clipboard", object())

        self.assertTrue(shown)
        self.assertEqual(opened, [])

    def test_existing_top_level_window_is_reused_when_surface_map_is_empty(self) -> None:
        class FakeWindow(QObject):
            def __init__(self, plugin_id: str, visible: bool) -> None:
                super().__init__()
                self.setProperty("pluginId", plugin_id)
                self.setProperty("retainOnClose", True)
                self._visible = visible
                self.closed = False

            def isVisible(self) -> bool:
                return self._visible

            def close(self) -> None:
                self.closed = True
                self._visible = False

        hidden_duplicate = FakeWindow("clipboard", False)
        visible_window = FakeWindow("clipboard", True)
        other_window = FakeWindow("api-test", True)
        coordinator = PluginSurfaceCoordinator.__new__(PluginSurfaceCoordinator)
        coordinator._windows = {}
        coordinator._qt_app = SimpleNamespace(topLevelWindows=lambda: [hidden_duplicate, visible_window, other_window])

        surface = coordinator._get_live_surface("clipboard")

        self.assertIsNotNone(surface)
        self.assertIs(surface.window, visible_window)
        self.assertIs(coordinator._windows["clipboard"].window, visible_window)
        self.assertTrue(hidden_duplicate.closed)
        self.assertFalse(other_window.closed)

    def test_target_screen_prefers_focus_screen_over_cursor_screen(self) -> None:
        focus_screen = object()
        cursor_screen = object()
        launcher_screen = object()
        primary_screen = object()
        coordinator = PluginSurfaceCoordinator.__new__(PluginSurfaceCoordinator)
        coordinator._qt_app = SimpleNamespace(
            screenAt=lambda pos: focus_screen if pos == QPoint(10, 20) else cursor_screen,
            primaryScreen=lambda: primary_screen,
        )
        coordinator._launcher_window = SimpleNamespace(screen=lambda: launcher_screen)

        with patch("app.plugin_surface_coordinator.focused_window_point", return_value=QPoint(10, 20)):
            self.assertIs(coordinator._target_screen(), focus_screen)

    def test_target_screen_falls_back_to_cursor_screen_before_launcher_screen(self) -> None:
        cursor_screen = object()
        launcher_screen = object()
        primary_screen = object()
        coordinator = PluginSurfaceCoordinator.__new__(PluginSurfaceCoordinator)
        coordinator._qt_app = SimpleNamespace(
            screenAt=lambda _pos: cursor_screen,
            primaryScreen=lambda: primary_screen,
        )
        coordinator._launcher_window = SimpleNamespace(screen=lambda: launcher_screen)

        with patch("app.plugin_surface_coordinator.focused_window_point", return_value=None):
            self.assertIs(coordinator._target_screen(), cursor_screen)

    def test_reused_window_moves_to_focus_screen_before_activation(self) -> None:
        class FakeWindow(QObject):
            def __init__(self, screen: object) -> None:
                super().__init__()
                self.setProperty("pluginId", "clipboard")
                self._screen = screen
                self.calls: list[str] = []

            def screen(self) -> object:
                return self._screen

            def width(self) -> int:
                return 720

            def height(self) -> int:
                return 520

            def setScreen(self, screen: object) -> None:
                self._screen = screen
                self.calls.append("setScreen")

            def show(self) -> None:
                self.calls.append("show")

            def raise_(self) -> None:
                self.calls.append("raise")

            def requestActivate(self) -> None:
                self.calls.append("activate")

        old_screen = object()
        target_screen = object()
        window = FakeWindow(old_screen)
        coordinator = PluginSurfaceCoordinator.__new__(PluginSurfaceCoordinator)
        coordinator._windows = {"clipboard": PluginWindowSurface(plugin_id="clipboard", window=window)}
        coordinator._qt_app = SimpleNamespace(
            topLevelWindows=lambda: [window],
            screenAt=lambda pos: target_screen if pos == QPoint(30, 40) else old_screen,
            primaryScreen=lambda: old_screen,
        )

        with (
            patch("app.plugin_surface_coordinator.focused_window_point", return_value=QPoint(30, 40)),
            patch("app.plugin_surface_coordinator._center_window_once") as center_window,
            patch("app.plugin_surface_coordinator.QTimer.singleShot"),
        ):
            shown = coordinator._show_window_surface("clipboard", object())

        self.assertTrue(shown)
        center_window.assert_called_once_with(window, target_screen, 720, 520)
        self.assertEqual(window.calls, ["setScreen", "show", "raise", "activate"])

    def test_reused_window_configures_and_native_activates_surface(self) -> None:
        class FakeWindow(QObject):
            def __init__(self) -> None:
                super().__init__()
                self.setProperty("pluginId", "clipboard")
                self.setProperty("alwaysOnTop", True)
                self.calls: list[str] = []

            def screen(self) -> object:
                return object()

            def show(self) -> None:
                self.calls.append("show")

            def raise_(self) -> None:
                self.calls.append("raise")

            def requestActivate(self) -> None:
                self.calls.append("request")

        window = FakeWindow()
        coordinator = PluginSurfaceCoordinator.__new__(PluginSurfaceCoordinator)
        coordinator._windows = {"clipboard": PluginWindowSurface(plugin_id="clipboard", window=window)}
        coordinator._qt_app = SimpleNamespace(topLevelWindows=lambda: [window], screenAt=lambda _pos: None)
        calls: list[str] = []
        coordinator._move_window_to_target_screen = lambda _window: calls.append("move")
        coordinator._configure_surface_window = lambda _window, *, force_top: calls.append(f"configure:{force_top}")

        with (
            patch("app.plugin_surface_coordinator._activate_macos_window", side_effect=lambda _window: calls.append("native") or True),
            patch("app.plugin_surface_coordinator.QTimer.singleShot"),
        ):
            shown = coordinator._show_window_surface("clipboard", object())

        self.assertTrue(shown)
        self.assertEqual(calls, ["move", "configure:True", "native"])
        self.assertEqual(window.calls, ["show", "raise", "request"])

    def test_delayed_surface_activation_reconfigures_window_level(self) -> None:
        class FakeWindow(QObject):
            def __init__(self) -> None:
                super().__init__()
                self.setProperty("alwaysOnTop", True)
                self.calls: list[str] = []

            def raise_(self) -> None:
                self.calls.append("raise")

            def requestActivate(self) -> None:
                self.calls.append("request")

        window = FakeWindow()
        coordinator = PluginSurfaceCoordinator.__new__(PluginSurfaceCoordinator)
        calls: list[str] = []
        coordinator._configure_surface_window = lambda _window, *, force_top: calls.append(f"configure:{force_top}")

        with patch("app.plugin_surface_coordinator._activate_macos_window", side_effect=lambda _window: calls.append("native") or True):
            coordinator._activate_surface_window(window)

        self.assertEqual(calls, ["configure:True", "native"])
        self.assertEqual(window.calls, ["raise", "request"])


class LauncherRuntimeCoordinatorTests(unittest.TestCase):
    def test_center_launcher_prefers_focus_screen_over_cursor_screen(self) -> None:
        from app.launcher_runtime_coordinator import LauncherRuntimeCoordinator

        class FakeWindow(QObject):
            def __init__(self) -> None:
                super().__init__()
                self.calls: list[str] = []

            def width(self) -> int:
                return 760

            def height(self) -> int:
                return 560

            def setScreen(self, screen: object) -> None:
                self.calls.append(("setScreen", screen))

            def screen(self) -> object:
                return object()

        focus_screen = object()
        cursor_screen = object()
        launcher = FakeWindow()
        coordinator = LauncherRuntimeCoordinator.__new__(LauncherRuntimeCoordinator)
        coordinator._launcher_window = launcher
        coordinator._qt_app = SimpleNamespace(
            screenAt=lambda pos: focus_screen if pos == QPoint(10, 20) else cursor_screen,
            primaryScreen=lambda: object(),
        )

        with (
            patch("app.launcher_runtime_coordinator.focused_window_point", return_value=QPoint(10, 20)),
            patch("app.launcher_runtime_coordinator._center_window_once") as center_window,
        ):
            coordinator._center_launcher_window()

        center_window.assert_called_once_with(launcher, focus_screen, 760, 560)
        self.assertEqual(launcher.calls, [("setScreen", focus_screen)])

    def test_show_launcher_reconfigures_macos_window_after_show(self) -> None:
        from app.launcher_runtime_coordinator import LauncherRuntimeCoordinator

        class FakeWindow(QObject):
            def __init__(self) -> None:
                super().__init__()
                self.calls: list[str] = []

            def width(self) -> int:
                return 760

            def height(self) -> int:
                return 560

            def show(self) -> None:
                self.calls.append("show")

            def raise_(self) -> None:
                self.calls.append("raise")

            def requestActivate(self) -> None:
                self.calls.append("request")

        launcher = FakeWindow()
        coordinator = LauncherRuntimeCoordinator.__new__(LauncherRuntimeCoordinator)
        coordinator._launcher_window = launcher
        coordinator._configure_launcher_window_for_macos = lambda *, force=False: launcher.calls.append(f"configure:{force}")
        coordinator._center_launcher_window = lambda: launcher.calls.append("center")
        coordinator._activate_launcher_window_native = lambda: launcher.calls.append("native")

        result = coordinator._show_launcher_window(activate=True)

        self.assertGreaterEqual(result["elapsedMs"], 0)
        self.assertEqual(launcher.calls, ["configure:False", "center", "show", "configure:True", "raise", "native", "request"])


class ClipboardServiceTests(unittest.TestCase):
    def test_latest_context_item_prefers_captured_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_data_dir = os.environ.get("PY_DESKTOP_TOOLS_DATA_DIR")
            old_log_dir = os.environ.get("PY_DESKTOP_TOOLS_LOG_DIR")
            os.environ["PY_DESKTOP_TOOLS_DATA_DIR"] = str(Path(tmp) / "data")
            os.environ["PY_DESKTOP_TOOLS_LOG_DIR"] = str(ROOT / ".tmp" / "test_logs")
            storage = StorageManager(Path(tmp))
            try:
                service = ClipboardService(
                    storage.database("clipboard.db"),
                    settings_store=storage.dict_store("clipboard/settings"),
                )
                service.store.capture_draft(
                    type(
                        "Draft",
                        (),
                        {
                            "item_type": "text",
                            "content": "hello",
                            "preview": "hello",
                            "metadata": {},
                            "image_bytes": None,
                        },
                    )()
                )

                item = service.latest_context_item()
                self.assertIsNotNone(item)
                self.assertEqual(item["content"], "hello")
            finally:
                if "service" in locals():
                    service.close()
                if old_data_dir is None:
                    os.environ.pop("PY_DESKTOP_TOOLS_DATA_DIR", None)
                else:
                    os.environ["PY_DESKTOP_TOOLS_DATA_DIR"] = old_data_dir
                if old_log_dir is None:
                    os.environ.pop("PY_DESKTOP_TOOLS_LOG_DIR", None)
                else:
                    os.environ["PY_DESKTOP_TOOLS_LOG_DIR"] = old_log_dir

    def test_repeated_clip_replaces_old_entry_and_preserves_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = StorageManager(Path(tmp))
            service = ClipboardService(
                storage.database("clipboard.db"),
                settings_store=storage.dict_store("clipboard/settings"),
            )
            try:
                service.store.add_text("alpha")
                first = service.latest_item()
                self.assertIsNotNone(first)
                service.toggle_pin(int(first["id"]))
                service.store.add_text("beta")
                service.store.add_text("alpha")

                rows = service.search("")
                alpha_rows = [row for row in rows if row["content"] == "alpha"]
                self.assertEqual(len(alpha_rows), 1)
                self.assertEqual(rows[0]["content"], "alpha")
                self.assertTrue(rows[0]["pinned"])
            finally:
                service.close()

    def test_copy_item_promotes_existing_history_item(self) -> None:
        class RecordingBackend:
            def __init__(self) -> None:
                self.writes: list[str] = []

            def start(self, on_change) -> None:
                del on_change

            def stop(self) -> None:
                return

            def read_current(self):
                return None

            def write_text(self, text: str) -> None:
                self.writes.append(text)

            def write_files(self, paths) -> None:
                del paths

            def write_image(self, path: str) -> None:
                del path

            def clear(self) -> None:
                return

        with tempfile.TemporaryDirectory() as tmp:
            backend = RecordingBackend()
            storage = StorageManager(Path(tmp))
            service = ClipboardService(
                storage.database("clipboard.db"),
                settings_store=storage.dict_store("clipboard/settings"),
                backend=backend,
            )
            try:
                service.store.add_text("alpha")
                alpha = service.latest_item()
                self.assertIsNotNone(alpha)
                service.store.add_text("beta")

                self.assertTrue(service.copy_item_by_id(int(alpha["id"])))

                self.assertEqual(backend.writes, ["alpha"])
                self.assertEqual(service.latest_item()["content"], "alpha")
                self.assertEqual(
                    len([row for row in service.search("") if row["content"] == "alpha"]),
                    1,
                )
            finally:
                service.close()

    def test_search_filter_type_is_applied_before_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = StorageManager(Path(tmp))
            service = ClipboardService(
                storage.database("clipboard.db"),
                settings_store=storage.dict_store("clipboard/settings"),
            )
            try:
                service.store.add_files(["/tmp/readme.txt"])
                for index in range(120):
                    service.store.add_text(f"text-{index}")

                rows = service.search("", filter_type="files")

                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["itemType"], "files")
            finally:
                service.close()


class ClipboardViewModelTests(unittest.TestCase):
    def test_image_item_uses_valid_file_url_and_clean_title(self) -> None:
        from features.clipboard.view_model import _file_url, _to_view_item

        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "clip.png"
            image_path.write_bytes(b"png")
            item = _to_view_item(
                {
                    "id": 1,
                    "itemType": "image",
                    "content": str(image_path),
                    "preview": "",
                    "metadata": {},
                    "createdAt": "",
                    "pinned": False,
                }
            )

            self.assertEqual(item["title"], "图片")
            self.assertEqual(item["imageUrl"], image_path.resolve().as_uri())
            self.assertEqual(_file_url(r"C:\Temp\clip.png"), "file:///C:/Temp/clip.png")

    def test_text_item_detects_useful_badges(self) -> None:
        from features.clipboard.view_model import _to_view_item

        item = _to_view_item(
            {
                "id": 1,
                "itemType": "text",
                "content": '{"token": "abc"}',
                "preview": '{"token": "abc"}',
                "metadata": {},
                "createdAt": "",
                "pinned": False,
            }
        )

        self.assertEqual(item["icon"], "qta:mdi6.code-json")
        self.assertIn("JSON", item["badges"])
        self.assertIn("敏感", item["badges"])
        self.assertEqual(item["stats"], "16 字符")

    def test_filter_type_limits_history_items(self) -> None:
        from features.clipboard.view_model import ClipboardWindowViewModel

        with tempfile.TemporaryDirectory() as tmp:
            storage = StorageManager(Path(tmp))
            service = ClipboardService(
                storage.database("clipboard.db"),
                settings_store=storage.dict_store("clipboard/settings"),
            )
            vm = ClipboardWindowViewModel(service)
            try:
                service.store.add_text("alpha")
                service.store.add_files(["/tmp/readme.txt"])
                vm.setFilterType("files")

                model = vm.historyModel
                self.assertEqual(model.count, 1)
                self.assertEqual(model.itemAt(0)["itemType"], "files")
            finally:
                vm.close()
                service.close()


class PythonTaskRunnerTests(unittest.TestCase):
    def test_runner_handles_success_error_and_cancel(self) -> None:
        runner = PythonTaskRunner(max_workers=1, thread_name_prefix="test-task")
        try:
            success = Event()
            errors: list[str] = []
            results: list[object] = []

            runner.start(
                lambda: "ok",
                on_success=lambda value: (results.append(value), success.set()),
                on_error=lambda exc: errors.append(str(exc)),
            )
            self.assertTrue(success.wait(2))
            self.assertEqual(results, ["ok"])
            self.assertEqual(errors, [])

            failed = Event()
            runner.start(
                lambda: (_ for _ in ()).throw(RuntimeError("boom")),
                on_error=lambda exc: (errors.append(str(exc)), failed.set()),
            )
            self.assertTrue(failed.wait(2))
            self.assertIn("boom", errors[-1])

            cancelled_called = Event()
            handle = runner.start(
                lambda task: "cancelled" if task.cancel_event.wait(1) else "done",
                on_success=lambda _value: cancelled_called.set(),
            )
            runner.cancel(handle.id)
            self.assertFalse(cancelled_called.wait(0.2))
        finally:
            runner.shutdown(wait=True)


class LoggingManagerTests(unittest.TestCase):
    def test_plugin_log_handler_creates_nested_directory(self) -> None:
        old_handlers = list(logging.getLogger().handlers)
        with tempfile.TemporaryDirectory() as tmp:
            manager = LoggingManager(
                app_name="test",
                app_version="test",
                log_dir=Path(tmp) / "logs",
                console=False,
            )
            try:
                logger = manager.for_plugin("api-test")
                logger.info("probe", "probe")
                self.assertTrue((Path(tmp) / "logs" / "plugins").is_dir())
                self.assertTrue((Path(tmp) / "logs" / "plugins" / "api-test.log").exists())
            finally:
                manager.shutdown()
                root = logging.getLogger()
                for handler in list(root.handlers):
                    root.removeHandler(handler)
                for handler in old_handlers:
                    root.addHandler(handler)


@unittest.skipUnless(sys.platform == "win32", "Windows hotkey tests require Windows")
class WindowsHotkeyTests(unittest.TestCase):
    def test_windows_hotkey_parses_common_sequences(self) -> None:
        from app.platform.windows.hotkey import MOD_ALT, MOD_CONTROL, MOD_SHIFT, parse_hotkey

        self.assertEqual(parse_hotkey("Alt+Space"), (MOD_ALT, 0x20))
        self.assertEqual(parse_hotkey("Ctrl+Shift+F12"), (MOD_CONTROL | MOD_SHIFT, 0x7B))
        self.assertIsNone(parse_hotkey("Alt"))

    def test_windows_hotkey_fallback_env_controls_hook(self) -> None:
        from app.platform.windows.hotkey import WinHotkeyManager

        manager = WinHotkeyManager(hotkey="Alt+Space")
        manager._native_registered = True
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PY_DESKTOP_TOOLS_HOTKEY_HOOK", None)
            self.assertTrue(manager._should_enable_fallback())
        manager = WinHotkeyManager(hotkey="Ctrl+Alt+K", hotkey_id=9)
        manager._native_registered = True
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PY_DESKTOP_TOOLS_HOTKEY_HOOK", None)
            self.assertFalse(manager._should_enable_fallback())
        with patch.dict(os.environ, {"PY_DESKTOP_TOOLS_HOTKEY_HOOK": "1"}, clear=False):
            self.assertTrue(manager._should_enable_fallback())
        manager._native_registered = False
        with patch.dict(os.environ, {"PY_DESKTOP_TOOLS_HOTKEY_HOOK": "0"}, clear=False):
            self.assertFalse(manager._should_enable_fallback())
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PY_DESKTOP_TOOLS_HOTKEY_HOOK", None)
            self.assertTrue(manager._should_enable_fallback())


class MacHotkeyTests(unittest.TestCase):
    def test_macos_hotkey_parses_common_sequences(self) -> None:
        from app.platform.macos.hotkey import _parse_hotkey

        self.assertEqual(_parse_hotkey("Alt+Space"), ({"alt"}, "space"))
        self.assertEqual(_parse_hotkey("Option+V"), ({"alt"}, "v"))
        self.assertEqual(_parse_hotkey("Cmd+Shift+F12"), ({"cmd", "shift"}, "f12"))
        self.assertIsNone(_parse_hotkey("Alt"))

    def test_macos_key_normalization_uses_virtual_key_before_option_char(self) -> None:
        from app.platform.macos.hotkey import _native_hotkey, _normalize_pressed_key

        self.assertEqual(_normalize_pressed_key(SimpleNamespace(vk=0x09, char="√")), "v")
        self.assertEqual(_normalize_pressed_key(SimpleNamespace(vk=0x31, char="\xa0")), "space")
        self.assertEqual(_normalize_pressed_key(SimpleNamespace(char="A")), "a")
        self.assertEqual(_normalize_pressed_key(SimpleNamespace(name="cmd_r")), "cmd")
        self.assertEqual(_native_hotkey(({"alt"}, "v")), (0x09, 1 << 11))

    def test_macos_hotkey_triggers_once_until_target_release(self) -> None:
        from app.platform.macos.hotkey import MacHotkeyManager

        manager = MacHotkeyManager(hotkey="Alt+V")
        calls: list[str] = []
        manager._target_modifiers = {"alt"}
        manager._target_key = "v"
        manager._queue_pressed = calls.append

        manager._handle_press(SimpleNamespace(vk=0x3A))
        manager._handle_press(SimpleNamespace(vk=0x09, char="√"))
        manager._handle_press(SimpleNamespace(vk=0x09, char="√"))
        manager._handle_release(SimpleNamespace(vk=0x09, char="√"))
        manager._handle_press(SimpleNamespace(vk=0x09, char="√"))

        self.assertEqual(calls, ["pynput", "pynput"])

    def test_macos_hotkey_does_not_trigger_when_modifier_pressed_after_target(self) -> None:
        from app.platform.macos.hotkey import MacHotkeyManager

        manager = MacHotkeyManager(hotkey="Alt+V")
        calls: list[str] = []
        manager._target_modifiers = {"alt"}
        manager._target_key = "v"
        manager._queue_pressed = calls.append

        manager._handle_press(SimpleNamespace(vk=0x09, char="v"))
        manager._handle_press(SimpleNamespace(vk=0x3A))
        manager._handle_press(SimpleNamespace(vk=0x09, char="√"))

        self.assertEqual(calls, [])


class PermissionApiTests(unittest.TestCase):
    def test_macos_accessibility_status_uses_system_api(self) -> None:
        from app.platform.common import permissions

        fake_services = SimpleNamespace(AXIsProcessTrusted=lambda: True)

        with (
            patch.object(permissions.sys, "platform", "darwin"),
            patch.dict(sys.modules, {"ApplicationServices": fake_services}),
        ):
            result = permissions.DefaultPermissionApi().accessibility_status()

        self.assertTrue(result.ok)
        self.assertEqual(result.data["status"], "authorized")

    def test_open_accessibility_settings_opens_privacy_anchor(self) -> None:
        from app.platform.common import permissions

        with (
            patch.object(permissions.sys, "platform", "darwin"),
            patch("app.platform.common.permissions.subprocess.Popen") as popen,
        ):
            result = permissions.DefaultPermissionApi().open_accessibility_settings()

        self.assertTrue(result.ok)
        self.assertEqual(
            [call.args[0] for call in popen.call_args_list],
            [
                ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"],
                ["open", "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_Accessibility"],
            ],
        )


class SystemSettingsViewModelTests(unittest.TestCase):
    def test_accessibility_status_and_open_settings_are_exposed(self) -> None:
        from features.system.view_model import SystemSettingsViewModel

        class Permissions:
            def __init__(self) -> None:
                self.opened = False

            def accessibility_status(self) -> PlatformResult:
                return PlatformResult(False, data={"status": "not_authorized"})

            def open_accessibility_settings(self) -> PlatformResult:
                self.opened = True
                return PlatformResult(True)

        permissions = Permissions()
        vm = SystemSettingsViewModel(permissions=permissions)

        self.assertFalse(vm.accessibilityAuthorized)
        self.assertEqual(vm.accessibilityStatusText, "辅助功能权限：未授权")
        self.assertTrue(vm.openAccessibilitySettings())
        self.assertTrue(permissions.opened)


class _FakeSignal:
    def connect(self, callback) -> None:
        self.callback = callback


class _FakeHotkeyManager:
    def __init__(self) -> None:
        self.hotkeyPressed = _FakeSignal()
        self.unregistered = 0
        self.registered: list[str] = []

    def register(self, hotkey: str | None = None) -> bool:
        self.registered.append(hotkey or "")
        return True

    def unregister(self) -> None:
        self.unregistered += 1


class _FakeHotkeyFactory:
    def __init__(self) -> None:
        self.managers: list[_FakeHotkeyManager] = []

    def create(self, *, parent: object | None, hotkey: str, hotkey_id: int) -> _FakeHotkeyManager:
        del parent, hotkey, hotkey_id
        manager = _FakeHotkeyManager()
        self.managers.append(manager)
        return manager

    def install_filter(self, app: object, manager: object) -> object | None:
        del app, manager
        return None


class _EmptyCommands:
    def commands(self) -> list:
        return []


class HotkeyCoordinatorTests(unittest.TestCase):
    def test_refresh_plugin_hotkeys_unregisters_existing_once(self) -> None:
        factory = _FakeHotkeyFactory()
        services = PlatformServices(
            info=object(),
            default_launcher_hotkey="Alt+Space",
            default_clipboard_hotkey="Alt+V",
            paths=object(),
            hotkey_factory=factory,
            app_indexer=object(),
            external_launcher=object(),
            system_commands=_EmptyCommands(),
            clipboard=object(),
            dialogs=object(),
            screen=object(),
            storage_factory=object(),
            dynamic_command_api_factory=object(),
            permissions=object(),
        )
        coordinator = HotkeyCoordinator(services, object())
        manifest = PluginManifest(
            id="demo",
            name="Demo",
            version="1",
            description="",
            icon="",
            entrypoint="runtime:create_runtime",
            qml_page="Demo.qml",
            commands=[CommandContribution(id="demo.open", title="Demo", hotkey="Ctrl+D")],
        )

        coordinator.refresh_plugin_hotkeys([manifest])
        first_plugin_manager = factory.managers[-1]
        coordinator.refresh_plugin_hotkeys([])

        self.assertEqual(first_plugin_manager.unregistered, 1)


if __name__ == "__main__":
    unittest.main()

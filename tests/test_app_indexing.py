from __future__ import annotations

from pathlib import Path
import plistlib
import sys
import tempfile
import unittest
from threading import Event
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.commands.app_index_service import AppIndexService
from app.commands.command_index_db import CommandIndexDb
from app.commands.command_service import CommandService
from app.platform.models import AppEntry
from app.storage import StorageManager


class AppIndexServiceTests(unittest.TestCase):
    def test_scan_writes_metadata_then_icons_to_database(self) -> None:
        class FakeAppIndexer:
            def __init__(self) -> None:
                self.calls: list[bool] = []

            def scan_apps(self, icon_dir=None, *, extract_icons: bool = True) -> list[AppEntry]:
                self.calls.append(extract_icons)
                icon_path = ""
                if extract_icons and icon_dir is not None:
                    icon_path = str(Path(icon_dir) / "demo.png")
                return [
                    AppEntry(
                        platform="macos",
                        name="Demo",
                        launch_path="/Applications/Demo.app",
                        bundle_id="com.example.demo",
                        icon_path=icon_path,
                    )
                ]

            def quick_signature(self) -> str:
                return "fake-signature"

        with tempfile.TemporaryDirectory() as tmp:
            indexer = FakeAppIndexer()
            db = CommandIndexDb(StorageManager(Path(tmp)).database("command_index.db"))
            completed = Event()
            callback_count = 0

            def mark_completed() -> None:
                nonlocal callback_count
                callback_count += 1
                if callback_count >= 2:
                    completed.set()

            service = AppIndexService(db, SimpleNamespace(app_indexer=indexer))
            service.on_scan_completed(mark_completed)
            try:
                self.assertTrue(service.start_scan())
                self.assertTrue(completed.wait(2))
                rows = db.search_apps("Demo")
                self.assertEqual(indexer.calls, [False, True])
                self.assertEqual(rows[0]["iconPath"], str(Path(tmp) / "app_icons" / "demo.png"))
            finally:
                service.shutdown()
                db.close()

    def test_change_check_scans_only_when_signature_changes(self) -> None:
        class FakeAppIndexer:
            def __init__(self) -> None:
                self.signature = "same"
                self.calls: list[bool] = []

            def scan_apps(self, icon_dir=None, *, extract_icons: bool = True) -> list[AppEntry]:
                self.calls.append(extract_icons)
                icon_path = ""
                if extract_icons and icon_dir is not None:
                    icon_path = str(Path(icon_dir) / "demo.png")
                return [
                    AppEntry(
                        platform="macos",
                        name="Demo",
                        launch_path="/Applications/Demo.app",
                        icon_path=icon_path,
                    )
                ]

            def quick_signature(self) -> str:
                return self.signature

        with tempfile.TemporaryDirectory() as tmp:
            indexer = FakeAppIndexer()
            db = CommandIndexDb(StorageManager(Path(tmp)).database("command_index.db"))
            db.sync_apps([indexer.scan_apps(extract_icons=False)[0].to_db_dict()])
            indexer.calls.clear()
            db.set_app_index_meta("app_index_signature", "same")
            service = AppIndexService(db, SimpleNamespace(app_indexer=indexer))
            try:
                self.assertTrue(service.start_change_check(force=True))
                self.assertFalse(Event().wait(0.2))
                self.assertEqual(indexer.calls, [])

                completed = Event()
                callback_count = 0

                def mark_completed() -> None:
                    nonlocal callback_count
                    callback_count += 1
                    if callback_count >= 2:
                        completed.set()

                service.on_scan_completed(mark_completed)
                indexer.signature = "changed"
                self.assertTrue(service.start_change_check(force=True))
                self.assertTrue(completed.wait(2))
                self.assertEqual(indexer.calls, [False, True])
                self.assertEqual(db.get_app_index_meta("app_index_signature"), "changed")
            finally:
                service.shutdown()
                db.close()


class CommandIndexDbTests(unittest.TestCase):
    def test_app_search_supports_chinese_english_and_initial_queries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = CommandIndexDb(StorageManager(Path(tmp)).database("command_index.db"))
            try:
                db.sync_apps(
                    [
                        {
                            "platform": "macos",
                            "name": "微信",
                            "launch_path": "/Applications/WeChat.app",
                            "bundle_id": "com.tencent.xinWeChat",
                            "icon_path": "",
                            "aliases": ["WeChat"],
                        },
                        {
                            "platform": "macos",
                            "name": "Visual Studio Code",
                            "launch_path": "/Applications/Visual Studio Code.app",
                            "bundle_id": "com.microsoft.VSCode",
                            "icon_path": "",
                            "aliases": ["VS Code"],
                        },
                        {
                            "platform": "macos",
                            "name": "QQ音乐",
                            "launch_path": "/Applications/QQMusic.app",
                            "bundle_id": "com.tencent.QQMusic",
                            "icon_path": "",
                            "aliases": ["QQ Music"],
                        },
                    ]
                )

                self.assertEqual(db.search_apps("微信")[0]["name"], "微信")
                self.assertEqual(db.search_apps("wechat")[0]["name"], "微信")
                self.assertEqual(db.search_apps("wx")[0]["name"], "微信")
                self.assertEqual(db.search_apps("we")[0]["name"], "微信")
                self.assertEqual(db.search_apps("vsc")[0]["name"], "Visual Studio Code")
                self.assertEqual(db.search_apps("qqyy")[0]["name"], "QQ音乐")

                platform = SimpleNamespace(
                    app_indexer=SimpleNamespace(
                        scan_apps=lambda *args, **kwargs: [],
                        quick_signature=lambda: "same",
                    ),
                    system_commands=SimpleNamespace(commands=lambda: []),
                )
                service = CommandService([], db, platform_services=platform)
                try:
                    self.assertEqual(service.search("wechat")[0]["name"], "微信")
                    self.assertEqual(service.search("vsc")[0]["name"], "Visual Studio Code")
                finally:
                    service.shutdown()
            finally:
                db.close()


class SystemSettingsViewModelTests(unittest.TestCase):
    def test_rescan_applications_delegates_to_command_service(self) -> None:
        from features.system.view_model import SystemSettingsViewModel

        class FakeCommandService:
            app_scan_running = False

            def __init__(self) -> None:
                self.force = False
                self.callbacks = []

            def on_app_scan_completed(self, callback) -> None:
                self.callbacks.append(callback)

            def count_apps(self) -> int:
                return 7

            def start_app_scan(self, *, force: bool = False) -> bool:
                self.force = force
                self.app_scan_running = True
                return True

        service = FakeCommandService()
        view_model = SystemSettingsViewModel(service)

        self.assertEqual(view_model.appCount, 7)
        self.assertFalse(view_model.appScanRunning)
        self.assertTrue(view_model.rescanApplications())
        self.assertTrue(service.force)
        self.assertTrue(view_model.appScanRunning)
        self.assertEqual(len(service.callbacks), 1)


class MacOSAppIndexerTests(unittest.TestCase):
    def test_macos_indexer_skips_apps_nested_inside_app_bundles(self) -> None:
        from app.platform.macos.apps import MacOSAppIndexer

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main_app = root / "QQ.app"
            helper_app = main_app / "Contents" / "Frameworks" / "QQ Helper.app"
            visible_app = root / "Tools" / "Visible.app"

            for app_dir, name, bundle_id in [
                (main_app, "QQ", "com.tencent.qq"),
                (helper_app, "QQ Helper", "com.tencent.qq.helper"),
                (visible_app, "Visible", "com.example.visible"),
            ]:
                contents = app_dir / "Contents"
                contents.mkdir(parents=True)
                with (contents / "Info.plist").open("wb") as file_obj:
                    plistlib.dump(
                        {
                            "CFBundleDisplayName": name,
                            "CFBundleIdentifier": bundle_id,
                        },
                        file_obj,
                    )

            apps = MacOSAppIndexer(app_dirs=[root]).scan_apps(extract_icons=False)
            names = {app.name for app in apps}

            self.assertEqual(names, {"QQ", "Visible"})

    def test_macos_indexer_prefers_chinese_localized_name_and_keeps_english_alias(self) -> None:
        from app.platform.macos.apps import MacOSAppIndexer

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app_dir = root / "Demo.app"
            contents = app_dir / "Contents"
            resources = contents / "Resources"
            zh_resources = resources / "zh_CN.lproj"
            en_resources = resources / "en.lproj"
            zh_resources.mkdir(parents=True)
            en_resources.mkdir(parents=True)
            with (contents / "Info.plist").open("wb") as file_obj:
                plistlib.dump(
                    {
                        "CFBundleDisplayName": "DemoBase",
                        "CFBundleIdentifier": "com.example.demo",
                    },
                    file_obj,
                )
            (zh_resources / "InfoPlist.strings").write_bytes(
                '"CFBundleDisplayName" = "示例";'.encode("utf-16")
            )
            (en_resources / "InfoPlist.strings").write_text(
                '"CFBundleDisplayName" = "Demo";',
                encoding="utf-8",
            )

            apps = MacOSAppIndexer(app_dirs=[root]).scan_apps(extract_icons=False)

            self.assertEqual(len(apps), 1)
            self.assertEqual(apps[0].name, "示例")
            self.assertIn("Demo", apps[0].aliases)
            self.assertIn("DemoBase", apps[0].aliases)

    def test_macos_indexer_reads_unquoted_info_plist_strings_keys(self) -> None:
        from app.platform.macos.apps import MacOSAppIndexer

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app_dir = root / "Feishu.app"
            contents = app_dir / "Contents"
            resources = contents / "Resources" / "zh_CN.lproj"
            resources.mkdir(parents=True)
            with (contents / "Info.plist").open("wb") as file_obj:
                plistlib.dump(
                    {
                        "CFBundleDisplayName": "Lark",
                        "CFBundleName": "Feishu",
                        "CFBundleIdentifier": "com.larksuite.feishu",
                    },
                    file_obj,
                )
            (resources / "InfoPlist.strings").write_text(
                'CFBundleDisplayName = "飞书";\nCFBundleName = "飞书";\n',
                encoding="utf-8",
            )

            apps = MacOSAppIndexer(app_dirs=[root]).scan_apps(extract_icons=False)

            self.assertEqual(len(apps), 1)
            self.assertEqual(apps[0].name, "飞书")
            self.assertIn("Lark", apps[0].aliases)
            self.assertIn("Feishu", apps[0].aliases)

    def test_macos_indexer_extracts_png_icon_from_bundle_resources(self) -> None:
        from PIL import Image
        from app.platform.macos.apps import MacOSAppIndexer

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app_dir = root / "Demo.app"
            resources = app_dir / "Contents" / "Resources"
            resources.mkdir(parents=True)
            with (app_dir / "Contents" / "Info.plist").open("wb") as file_obj:
                plistlib.dump(
                    {
                        "CFBundleDisplayName": "Demo",
                        "CFBundleIdentifier": "com.example.demo",
                        "CFBundleIconFile": "AppIcon.png",
                    },
                    file_obj,
                )
            Image.new("RGBA", (128, 128), (37, 99, 235, 255)).save(resources / "AppIcon.png")

            icon_dir = root / "icons"
            apps = MacOSAppIndexer(app_dirs=[root]).scan_apps(icon_dir, extract_icons=True)

            self.assertEqual(len(apps), 1)
            self.assertEqual(apps[0].name, "Demo")
            self.assertTrue(apps[0].icon_path)
            self.assertTrue(Path(apps[0].icon_path).is_file())

    def test_macos_quick_signature_changes_when_app_bundle_set_changes(self) -> None:
        from app.platform.macos.apps import MacOSAppIndexer

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app_dir = root / "Demo.app" / "Contents"
            app_dir.mkdir(parents=True)
            with (app_dir / "Info.plist").open("wb") as file_obj:
                plistlib.dump({"CFBundleDisplayName": "Demo"}, file_obj)

            indexer = MacOSAppIndexer(app_dirs=[root])
            first = indexer.quick_signature()

            other_dir = root / "Other.app" / "Contents"
            other_dir.mkdir(parents=True)
            with (other_dir / "Info.plist").open("wb") as file_obj:
                plistlib.dump({"CFBundleDisplayName": "Other"}, file_obj)

            self.assertNotEqual(first, indexer.quick_signature())


if __name__ == "__main__":
    unittest.main()

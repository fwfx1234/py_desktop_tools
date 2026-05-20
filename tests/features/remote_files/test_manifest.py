from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from app.plugins.manifest_loader import load_manifest_file
from app.storage import StorageManager
from features.remote_files.view_model import RemoteFilesViewModel


def test_remote_files_manifest_uses_window_mode() -> None:
    manifest = load_manifest_file(Path("src/features/remote_files/plugin.json"))

    assert manifest.id == "remote-files"
    assert manifest.context_property == "remoteFilesVm"
    assert manifest.window_options["width"] == 0.86
    assert manifest.primary_command.launch_mode == "window"


def test_remote_files_qml_loads(tmp_path) -> None:
    class AppStub(QObject):
        @Property(str, constant=True)
        def theme(self) -> str:
            return "dark"

    app = QApplication.instance() or QApplication([])
    engine = QQmlApplicationEngine()
    app_stub = AppStub()
    vm = RemoteFilesViewModel(StorageManager(tmp_path).database("remote_files.db", check_same_thread=False))
    engine.rootContext().setContextProperty("app", app_stub)
    engine.rootContext().setContextProperty("remoteFilesVm", vm)

    engine.load(QUrl.fromLocalFile(str(Path("src/features/remote_files/RemoteFilesPage.qml").resolve())))
    app.processEvents()

    try:
        assert engine.rootObjects()
    finally:
        vm.dispose()

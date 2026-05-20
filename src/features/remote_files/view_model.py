from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from app.concurrency import PythonTaskRunner
from app.logging import get_logger
from app.storage import SQLiteDatabase

from .service import RemoteFilesService


class RemoteFilesViewModel(QObject):
    profilesChanged = Signal()
    connectionStateChanged = Signal()
    localPathChanged = Signal()
    remotePathChanged = Signal()
    localItemsChanged = Signal()
    remoteItemsChanged = Signal()
    transfersChanged = Signal()
    statusMessageChanged = Signal()
    terminalBridgeChanged = Signal()
    _uiCallback = Signal(object)

    def __init__(self, database: SQLiteDatabase) -> None:
        super().__init__()
        self._log = get_logger("features.remote_files.view_model", plugin_id="remote-files")
        self._disposed = False
        self._uiCallback.connect(self._run_ui_callback)
        self._runner = PythonTaskRunner(max_workers=4, thread_name_prefix="remote-files")
        self._profiles: list[dict] = []
        self._connection_state: dict = {"status": "disconnected", "profileId": "", "protocol": "", "host": "", "message": ""}
        self._local_path = ""
        self._remote_path = "/"
        self._local_items: list[dict] = []
        self._remote_items: list[dict] = []
        self._transfers: list[dict] = []
        self._status_message = ""
        self._service = RemoteFilesService(
            database,
            on_transfers_updated=lambda items: self._post_ui(lambda: self._set_transfers(items)),
            on_message=lambda message: self._post_ui(lambda: self._set_status_message(message)),
        )
        self._profiles = self._service.list_profiles()
        self._log.info("remote_files.viewmodel.ready", "远程文件插件 ViewModel 已初始化", profileCount=len(self._profiles))
        self._bind_terminal_bridge()
        self._run_background(
            lambda: self._service.change_local_path(""),
            on_success=self._apply_result,
        )

    profiles = Property("QVariantList", lambda self: self._profiles, notify=profilesChanged)
    connectionState = Property("QVariantMap", lambda self: self._connection_state, notify=connectionStateChanged)
    localPath = Property(str, lambda self: self._local_path, notify=localPathChanged)
    remotePath = Property(str, lambda self: self._remote_path, notify=remotePathChanged)
    localItems = Property("QVariantList", lambda self: self._local_items, notify=localItemsChanged)
    remoteItems = Property("QVariantList", lambda self: self._remote_items, notify=remoteItemsChanged)
    transfers = Property("QVariantList", lambda self: self._transfers, notify=transfersChanged)
    statusMessage = Property(str, lambda self: self._status_message, notify=statusMessageChanged)
    terminalBridge = Property(QObject, lambda self: self._service.terminal_bridge, notify=terminalBridgeChanged)

    @Slot()
    def reloadProfiles(self) -> None:
        self._log.debug("remote_files.profiles.reload", "重新加载远程连接配置")
        self._profiles = self._service.list_profiles()
        self.profilesChanged.emit()

    @Slot("QVariantMap")
    def saveProfile(self, payload) -> None:
        data = dict(payload or {})
        self._log.info(
            "remote_files.profile.save_requested",
            "保存远程连接配置请求",
            profileId=str(data.get("id") or ""),
            protocol=str(data.get("protocol") or ""),
            host=str(data.get("host") or ""),
        )
        self._run_background(
            lambda: self._service.save_profile(data),
            on_success=lambda profiles: self._set_profiles(profiles),
        )

    @Slot(str)
    def deleteProfile(self, profileId: str) -> None:
        self._log.info("remote_files.profile.delete_requested", "删除远程连接配置请求", profileId=profileId)
        self._run_background(
            lambda: self._service.delete_profile(profileId),
            on_success=lambda profiles: self._set_profiles(profiles),
        )

    @Slot(str)
    def connectProfile(self, profileId: str) -> None:
        self._log.info("remote_files.connect.requested", "连接请求", profileId=profileId)
        self._set_status_message("连接中")
        self._set_connection_state({"status": "connecting", "profileId": profileId, "protocol": "", "host": "", "message": "连接中"})
        self._run_background(
            lambda: self._service.connect(profileId),
            on_success=lambda result: (self._apply_result(result), self._set_connection_state(self._service.connection_state()), self.reloadProfiles()),
        )

    @Slot()
    def disconnect(self) -> None:
        self._log.info("remote_files.disconnect.requested", "断开连接请求", profileId=self._connection_state.get("profileId", ""))
        self._run_background(
            self._service.disconnect,
            on_success=lambda _: self._set_connection_state(self._service.connection_state()),
        )

    @Slot()
    def refreshAll(self) -> None:
        self._log.info("remote_files.refresh.requested", "刷新请求", localPath=self._local_path, remotePath=self._remote_path)
        self._run_background(
            lambda: self._service.refresh(self._local_path, self._remote_path),
            on_success=self._apply_result,
        )

    @Slot(str)
    def changeLocalPath(self, path: str) -> None:
        self._log.debug("remote_files.local.change_path_requested", "切换本地目录请求", localPath=path)
        self._run_background(
            lambda: self._service.change_local_path(path),
            on_success=self._apply_result,
        )

    @Slot(str)
    def changeRemotePath(self, path: str) -> None:
        self._log.info("remote_files.remote.change_path_requested", "切换远程目录请求", remotePath=path)
        self._run_background(
            lambda: self._service.change_remote_path(path),
            on_success=self._apply_result,
        )

    @Slot("QVariantList")
    def uploadFiles(self, localPaths) -> None:
        paths = [str(item) for item in (localPaths or [])]
        self._log.info("remote_files.upload.requested", "上传文件请求", fileCount=len(paths), remotePath=self._remote_path)
        self._run_background(
            lambda: self._service.upload(paths, self._remote_path),
            on_success=lambda _: self._set_status_message("已加入上传队列"),
        )

    @Slot("QVariantList")
    def uploadPaths(self, localPaths) -> None:
        cleaned = [self._normalize_drop_path(item) for item in (localPaths or [])]
        cleaned = [path for path in cleaned if path]
        self._log.info(
            "remote_files.upload_paths.requested",
            "拖拽上传请求",
            pathCount=len(cleaned),
            remotePath=self._remote_path,
        )
        if not cleaned:
            return
        self._run_background(
            lambda: self._service.upload_paths(cleaned, self._remote_path),
            on_success=lambda ids: self._set_status_message(
                f"已加入上传队列 ({len(ids)} 个文件)" if ids else "未发现可上传的文件"
            ),
        )

    @staticmethod
    def _normalize_drop_path(value) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if text.startswith("file://"):
            import os
            from urllib.parse import unquote, urlparse

            parsed = urlparse(text)
            text = unquote(parsed.path or "")
            if os.name == "nt" and text.startswith("/") and len(text) > 2 and text[2] == ":":
                text = text[1:]
        return text

    @Slot("QVariantList")
    def downloadFiles(self, remoteItems) -> None:
        items = [dict(item) for item in (remoteItems or [])]
        self._log.info("remote_files.download.requested", "下载文件请求", itemCount=len(items), localPath=self._local_path)
        self._run_background(
            lambda: self._service.download(items, self._local_path),
            on_success=lambda _: self._set_status_message("已加入下载队列"),
        )

    @Slot("QVariantList", str)
    def downloadFilesTo(self, remoteItems, targetDir) -> None:
        items = [dict(item) for item in (remoteItems or [])]
        target = self._normalize_drop_path(targetDir)
        self._log.info(
            "remote_files.download_to.requested",
            "下载到指定目录请求",
            itemCount=len(items),
            targetDir=target,
        )
        if not items or not target:
            return
        self._run_background(
            lambda: self._service.download_to(items, target),
            on_success=lambda _: self._set_status_message(f"已加入下载队列 → {target}"),
        )

    @Slot()
    def syncRemoteFromTerminal(self) -> None:
        """One-shot: jump remote pane to the terminal's current directory."""

        bridge = self._service.terminal_bridge
        current = bridge.current_working_dir() if hasattr(bridge, "current_working_dir") else ""
        if current:
            self._log.info("remote_files.sync_terminal", "使用缓存的终端目录", remotePath=current)
            self.changeRemotePath(current)
            return
        self._log.info("remote_files.sync_terminal.probe", "向终端发送 pwd 探测")
        self._pending_terminal_sync = True
        if hasattr(bridge, "requestWorkingDir"):
            bridge.requestWorkingDir()
        self._set_status_message("正在向终端请求当前目录…")

    def _bind_terminal_bridge(self) -> None:
        bridge = self._service.terminal_bridge
        signal = getattr(bridge, "workingDirChanged", None)
        if signal is not None:
            signal.connect(self._on_terminal_dir_changed)
        self._pending_terminal_sync = False

    def _on_terminal_dir_changed(self, path: str) -> None:
        text = str(path or "")
        if not text:
            return
        self._log.debug("remote_files.terminal.cwd", "终端工作目录更新", remotePath=text)
        if not self._pending_terminal_sync:
            return
        self._pending_terminal_sync = False
        if self._connection_state.get("status") == "connected":
            self.changeRemotePath(text)

    @Slot(str)
    def cancelTransfer(self, transferId: str) -> None:
        self._log.info("remote_files.transfer.cancel_requested", "取消传输请求", transferId=transferId)
        self._service.transfers.cancel(transferId)

    @Slot()
    def clearFinishedTransfers(self) -> None:
        self._log.info("remote_files.transfer.clear_finished", "清理已完成传输")
        self._service.transfers.clear_finished()

    @Slot(str)
    def mkdirRemote(self, name: str) -> None:
        clean = str(name or "").strip().strip("/")
        if not clean:
            return
        target = self._remote_path.rstrip("/") + "/" + clean if self._remote_path != "/" else "/" + clean
        self._log.info("remote_files.remote.mkdir_requested", "创建远程目录请求", remotePath=target)
        self._run_background(
            lambda: self._service.mkdir_remote(target),
            on_success=lambda _: self.changeRemotePath(self._remote_path),
        )

    @Slot(str, str)
    def renameRemote(self, path: str, name: str) -> None:
        self._log.info("remote_files.remote.rename_requested", "重命名远程项目请求", remotePath=path, newName=name)
        self._run_background(
            lambda: self._service.rename_remote(path, name),
            on_success=lambda _: self.changeRemotePath(self._remote_path),
        )

    @Slot("QVariantList")
    def deleteRemote(self, items) -> None:
        data = [dict(item) for item in (items or [])]
        self._log.info("remote_files.remote.delete_requested", "删除远程项目请求", itemCount=len(data))
        self._run_background(
            lambda: self._service.delete_remote(data),
            on_success=lambda _: self.changeRemotePath(self._remote_path),
        )

    @Slot()
    def openTerminal(self) -> None:
        self._log.info("remote_files.terminal.open_requested", "打开 SSH 终端请求", profileId=self._connection_state.get("profileId", ""))
        self._run_background(
            self._service.open_terminal,
            on_success=lambda _: self._set_status_message("终端已连接"),
        )

    @Slot()
    def closeTerminal(self) -> None:
        self._log.info("remote_files.terminal.close_requested", "关闭 SSH 终端请求")
        self._service.terminal_bridge.close()
        self._set_status_message("终端已关闭")

    def dispose(self) -> None:
        self._log.info("remote_files.viewmodel.dispose", "释放远程文件插件 ViewModel")
        self._disposed = True
        self._runner.shutdown(wait=False)
        self._service.close()

    def _run_background(self, fn, *, on_success=None) -> None:
        self._runner.start(
            fn,
            on_success=lambda result: self._post_ui(lambda: on_success(result) if on_success is not None else None),
            on_error=lambda exc: self._post_ui(lambda: self._handle_error(exc)),
        )

    def _apply_result(self, result) -> None:
        if result is None:
            return
        if result.local_items is not None:
            self._local_items = result.local_items
            self.localItemsChanged.emit()
        if result.remote_items is not None:
            self._remote_items = result.remote_items
            self.remoteItemsChanged.emit()
        if result.local_path:
            self._local_path = result.local_path
            self.localPathChanged.emit()
        if result.remote_path:
            self._remote_path = result.remote_path
            self.remotePathChanged.emit()
        if result.message:
            self._set_status_message(result.message)

    def _set_profiles(self, profiles: list[dict]) -> None:
        self._profiles = list(profiles)
        self.profilesChanged.emit()

    def _set_connection_state(self, state: dict) -> None:
        self._connection_state = dict(state or {})
        self.connectionStateChanged.emit()
        if self._connection_state.get("message"):
            self._set_status_message(str(self._connection_state.get("message") or ""))

    def _set_transfers(self, items: list[dict]) -> None:
        self._transfers = list(items)
        self.transfersChanged.emit()

    def _set_status_message(self, message: str) -> None:
        self._status_message = str(message or "")
        self.statusMessageChanged.emit()

    def _handle_error(self, exc: BaseException) -> None:
        message = str(exc)
        self._log.error(
            "remote_files.operation.failed",
            "远程文件操作失败",
            error=message,
            connectionStatus=self._connection_state.get("status", ""),
            profileId=self._connection_state.get("profileId", ""),
        )
        self._set_status_message(message)
        if self._connection_state.get("status") == "connecting":
            self._set_connection_state({"status": "error", "profileId": self._connection_state.get("profileId", ""), "protocol": self._connection_state.get("protocol", ""), "host": self._connection_state.get("host", ""), "message": message})

    def _post_ui(self, fn) -> None:
        self._uiCallback.emit(fn)

    @Slot(object)
    def _run_ui_callback(self, fn: object) -> None:
        if not self._disposed and callable(fn):
            fn()

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from app.concurrency import PythonTaskRunner
from app.logging import get_logger
from app.storage import SQLiteDatabase

from .service import FtpSftpSshClientService


class FtpSftpSshClientViewModel(QObject):
    profilesChanged = Signal()
    sessionsChanged = Signal()
    activeProfileIdChanged = Signal()
    connectionStateChanged = Signal()
    localPathChanged = Signal()
    remotePathChanged = Signal()
    localItemsChanged = Signal()
    remoteItemsChanged = Signal()
    transfersChanged = Signal()
    statusMessageChanged = Signal()
    terminalBridgeChanged = Signal()
    ftpLogChanged = Signal()
    _uiCallback = Signal(object)

    def __init__(self, database: SQLiteDatabase) -> None:
        super().__init__()
        self._log = get_logger("features.ftp_sftp_ssh_client.view_model", plugin_id="ftp-sftp-ssh-client")
        self._disposed = False
        self._uiCallback.connect(self._run_ui_callback)
        self._runner = PythonTaskRunner(max_workers=4, thread_name_prefix="ftp-sftp-ssh-client")
        self._profiles: list[dict] = []
        self._status_message = ""
        self._service = FtpSftpSshClientService(
            database,
            on_transfers_updated=lambda pid, items: self._post_ui(lambda: self._on_transfers(pid, items)),
            on_message=lambda pid, message: self._post_ui(lambda: self._on_message(pid, message)),
            on_ftp_log=lambda pid, line: self._post_ui(lambda: self._on_ftp_log(pid, line)),
            on_snapshot_changed=lambda pid: self._post_ui(lambda: self._on_snapshot_changed(pid)),
        )
        self._profiles = self._service.list_profiles()
        self._log.info("ftp_sftp_ssh_client.viewmodel.ready", "FTP/SFTP/SSH 客户端插件 ViewModel 已初始化", profileCount=len(self._profiles))
        self._pending_terminal_sync = False
        self._bound_bridges: set[int] = set()

    # ------------------------ properties -------------------------------

    profiles = Property("QVariantList", lambda self: self._profiles, notify=profilesChanged)
    sessions = Property("QVariantList", lambda self: self._service.sessions_summary(), notify=sessionsChanged)
    activeProfileId = Property(str, lambda self: self._service.active_profile_id(), notify=activeProfileIdChanged)
    connectionState = Property("QVariantMap", lambda self: self._active_snapshot(), notify=connectionStateChanged)
    localPath = Property(str, lambda self: self._service.local_path_for(self._service.active_profile_id()), notify=localPathChanged)
    remotePath = Property(str, lambda self: self._service.remote_path_for(self._service.active_profile_id()), notify=remotePathChanged)
    localItems = Property("QVariantList", lambda self: self._service.local_items_for(self._service.active_profile_id()), notify=localItemsChanged)
    remoteItems = Property("QVariantList", lambda self: self._service.remote_items_for(self._service.active_profile_id()), notify=remoteItemsChanged)
    transfers = Property("QVariantList", lambda self: self._service.transfers_for(self._service.active_profile_id()), notify=transfersChanged)
    statusMessage = Property(str, lambda self: self._status_message, notify=statusMessageChanged)
    terminalBridge = Property(QObject, lambda self: self._service.terminal_bridge_for(self._service.active_profile_id()), notify=terminalBridgeChanged)
    ftpLog = Property("QVariantList", lambda self: self._service.ftp_log_for(self._service.active_profile_id()), notify=ftpLogChanged)

    def _active_snapshot(self) -> dict:
        pid = self._service.active_profile_id()
        if pid:
            return self._service.snapshot_for(pid)
        return {"status": "disconnected", "profileId": "", "protocol": "", "host": "", "message": ""}

    # ------------------------ slots: profiles --------------------------

    @Slot()
    def reloadProfiles(self) -> None:
        self._log.debug("ftp_sftp_ssh_client.profiles.reload", "重新加载远程连接配置")
        self._profiles = self._service.list_profiles()
        self.profilesChanged.emit()

    @Slot("QVariantMap")
    def saveProfile(self, payload) -> None:
        data = dict(payload or {})
        self._log.info(
            "ftp_sftp_ssh_client.profile.save_requested",
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
        self._log.info("ftp_sftp_ssh_client.profile.delete_requested", "删除远程连接配置请求", profileId=profileId)
        self._run_background(
            lambda: self._service.delete_profile(profileId),
            on_success=lambda profiles: (self._set_profiles(profiles), self._emit_all_active_changed()),
        )

    # ------------------------ slots: sessions --------------------------

    @Slot(str)
    def setActiveProfile(self, profileId: str) -> None:
        target = str(profileId or "")
        if target == self._service.active_profile_id():
            return
        if target and not self._service.has_session(target):
            self._service.set_active(target)
            self.activeProfileIdChanged.emit()
            self._emit_all_active_changed()
            return
        self._service.set_active(target)
        self.activeProfileIdChanged.emit()
        self._bind_terminal_bridge_for(target)
        self._emit_all_active_changed()

    @Slot(str)
    def connectProfile(self, profileId: str) -> None:
        self._log.info("ftp_sftp_ssh_client.connect.requested", "连接请求", profileId=profileId)
        self._set_status_message("连接中")
        self._service.set_active(profileId)
        self.activeProfileIdChanged.emit()
        self.sessionsChanged.emit()
        self._run_background(
            lambda: self._service.connect(profileId),
            on_success=lambda _result: (
                self._bind_terminal_bridge_for(profileId),
                self.sessionsChanged.emit(),
                self._emit_all_active_changed(),
                self.reloadProfiles(),
                self._auto_open_terminal(profileId),
            ),
        )

    def _auto_open_terminal(self, profile_id: str) -> None:
        snapshot = self._service.snapshot_for(profile_id)
        if (snapshot.get("protocol") or "").lower() != "sftp":
            return
        bridge = self._service.terminal_bridge_for(profile_id)
        if bridge is not None and hasattr(bridge, "is_attached") and bridge.is_attached():
            return
        self._run_background(
            lambda: self._service.open_terminal(profile_id),
            on_success=lambda _: (
                self._bind_terminal_bridge_for(profile_id),
                self.terminalBridgeChanged.emit(),
            ),
        )

    @Slot()
    def disconnect(self) -> None:
        self.disconnectProfile(self._service.active_profile_id())

    @Slot(str)
    def disconnectProfile(self, profileId: str) -> None:
        target = str(profileId or "") or self._service.active_profile_id()
        if not target:
            return
        self._log.info("ftp_sftp_ssh_client.disconnect.requested", "断开连接请求", profileId=target)
        self._run_background(
            lambda: self._service.disconnect(target),
            on_success=lambda _: (self.sessionsChanged.emit(), self.activeProfileIdChanged.emit(), self._emit_all_active_changed()),
        )

    @Slot()
    def refreshAll(self) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        local_path = self._service.local_path_for(pid)
        remote_path = self._service.remote_path_for(pid)
        self._log.info("ftp_sftp_ssh_client.refresh.requested", "刷新请求", profileId=pid, localPath=local_path, remotePath=remote_path)
        self._run_background(
            lambda: self._service.refresh(pid, local_path, remote_path),
            on_success=lambda _: self._emit_all_active_changed(),
        )

    @Slot(str)
    def changeLocalPath(self, path: str) -> None:
        pid = self._service.active_profile_id()
        self._log.debug("ftp_sftp_ssh_client.local.change_path_requested", "切换本地目录请求", profileId=pid, localPath=path)
        self._run_background(
            lambda: self._service.change_local_path(pid, path),
            on_success=lambda _: (self.localPathChanged.emit(), self.localItemsChanged.emit()),
        )

    @Slot(str)
    def changeRemotePath(self, path: str) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        self._log.info("ftp_sftp_ssh_client.remote.change_path_requested", "切换远程目录请求", profileId=pid, remotePath=path)
        self._run_background(
            lambda: self._service.change_remote_path(pid, path),
            on_success=lambda _: (self.remotePathChanged.emit(), self.remoteItemsChanged.emit()),
        )

    # ------------------------ slots: transfers -------------------------

    @Slot("QVariantList")
    def uploadFiles(self, localPaths) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        paths = [str(item) for item in (localPaths or [])]
        remote_dir = self._service.remote_path_for(pid)
        self._log.info("ftp_sftp_ssh_client.upload.requested", "上传文件请求", profileId=pid, fileCount=len(paths), remotePath=remote_dir)
        self._run_background(
            lambda: self._service.upload(pid, paths, remote_dir),
            on_success=lambda _: self._set_status_message("已加入上传队列"),
        )

    @Slot("QVariantList")
    def uploadPaths(self, localPaths) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        cleaned = [self._normalize_drop_path(item) for item in (localPaths or [])]
        cleaned = [path for path in cleaned if path]
        remote_dir = self._service.remote_path_for(pid)
        self._log.info(
            "ftp_sftp_ssh_client.upload_paths.requested",
            "拖拽上传请求",
            profileId=pid,
            pathCount=len(cleaned),
            remotePath=remote_dir,
        )
        if not cleaned:
            return
        self._run_background(
            lambda: self._service.upload_paths(pid, cleaned, remote_dir),
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
        pid = self._service.active_profile_id()
        if not pid:
            return
        items = [dict(item) for item in (remoteItems or [])]
        local_path = self._service.local_path_for(pid)
        self._log.info("ftp_sftp_ssh_client.download.requested", "下载文件请求", profileId=pid, itemCount=len(items), localPath=local_path)
        self._run_background(
            lambda: self._service.download(pid, items, local_path),
            on_success=lambda _: self._set_status_message("已加入下载队列"),
        )

    @Slot("QVariantList", str)
    def downloadFilesTo(self, remoteItems, targetDir) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        items = [dict(item) for item in (remoteItems or [])]
        target = self._normalize_drop_path(targetDir)
        self._log.info(
            "ftp_sftp_ssh_client.download_to.requested",
            "下载到指定目录请求",
            profileId=pid,
            itemCount=len(items),
            targetDir=target,
        )
        if not items or not target:
            return
        self._run_background(
            lambda: self._service.download_to(pid, items, target),
            on_success=lambda _: self._set_status_message(f"已加入下载队列 → {target}"),
        )

    @Slot()
    def syncRemoteFromTerminal(self) -> None:
        """One-shot: jump remote pane to the active terminal's current directory."""

        pid = self._service.active_profile_id()
        if not pid:
            return
        bridge = self._service.terminal_bridge_for(pid)
        if bridge is None:
            return
        current = bridge.current_working_dir() if hasattr(bridge, "current_working_dir") else ""
        if current:
            self._log.info("ftp_sftp_ssh_client.sync_terminal", "使用缓存的终端目录", profileId=pid, remotePath=current)
            self.changeRemotePath(current)
            return
        self._log.info("ftp_sftp_ssh_client.sync_terminal.probe", "向终端发送 pwd 探测", profileId=pid)
        self._pending_terminal_sync = True
        if hasattr(bridge, "requestWorkingDir"):
            bridge.requestWorkingDir()
        self._set_status_message("正在向终端请求当前目录…")

    def _bind_terminal_bridge_for(self, profile_id: str) -> None:
        bridge = self._service.terminal_bridge_for(profile_id)
        if bridge is None:
            return
        if id(bridge) in self._bound_bridges:
            return
        signal = getattr(bridge, "workingDirChanged", None)
        if signal is not None:
            signal.connect(self._on_terminal_dir_changed)
        self._bound_bridges.add(id(bridge))

    def _on_terminal_dir_changed(self, path: str) -> None:
        text = str(path or "")
        if not text:
            return
        if not self._pending_terminal_sync:
            return
        self._pending_terminal_sync = False
        self.changeRemotePath(text)

    @Slot(str)
    def cancelTransfer(self, transferId: str) -> None:
        pid = self._service.active_profile_id()
        self._log.info("ftp_sftp_ssh_client.transfer.cancel_requested", "取消传输请求", profileId=pid, transferId=transferId)
        self._service.cancel_transfer(pid, transferId)

    @Slot()
    def clearFinishedTransfers(self) -> None:
        pid = self._service.active_profile_id()
        self._log.info("ftp_sftp_ssh_client.transfer.clear_finished", "清理已完成传输", profileId=pid)
        self._service.clear_finished_transfers(pid)

    @Slot(str)
    def mkdirRemote(self, name: str) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        clean = str(name or "").strip().strip("/")
        if not clean:
            return
        remote_path = self._service.remote_path_for(pid)
        target = remote_path.rstrip("/") + "/" + clean if remote_path != "/" else "/" + clean
        self._log.info("ftp_sftp_ssh_client.remote.mkdir_requested", "创建远程目录请求", profileId=pid, remotePath=target)
        self._run_background(
            lambda: self._service.mkdir_remote(pid, target),
            on_success=lambda _: self.changeRemotePath(remote_path),
        )

    @Slot(str, str)
    def renameRemote(self, path: str, name: str) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        self._log.info("ftp_sftp_ssh_client.remote.rename_requested", "重命名远程项目请求", profileId=pid, remotePath=path, newName=name)
        remote_path = self._service.remote_path_for(pid)
        self._run_background(
            lambda: self._service.rename_remote(pid, path, name),
            on_success=lambda _: self.changeRemotePath(remote_path),
        )

    @Slot("QVariantList")
    def deleteRemote(self, items) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        data = [dict(item) for item in (items or [])]
        remote_path = self._service.remote_path_for(pid)
        self._log.info("ftp_sftp_ssh_client.remote.delete_requested", "删除远程项目请求", profileId=pid, itemCount=len(data))
        self._run_background(
            lambda: self._service.delete_remote(pid, data),
            on_success=lambda _: self.changeRemotePath(remote_path),
        )

    # ------------------------ slots: terminal --------------------------

    @Slot()
    def openTerminal(self) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        self._log.info("ftp_sftp_ssh_client.terminal.open_requested", "打开 SSH 终端请求", profileId=pid)
        self._run_background(
            lambda: self._service.open_terminal(pid),
            on_success=lambda _: (self._bind_terminal_bridge_for(pid), self.terminalBridgeChanged.emit(), self._set_status_message("终端已连接")),
        )

    @Slot()
    def closeTerminal(self) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        self._log.info("ftp_sftp_ssh_client.terminal.close_requested", "关闭 SSH 终端请求", profileId=pid)
        self._service.close_terminal(pid)
        self.terminalBridgeChanged.emit()
        self._set_status_message("终端已关闭")

    # ------------------------ slots: ftp log ---------------------------

    @Slot()
    def clearFtpLog(self) -> None:
        pid = self._service.active_profile_id()
        if not pid:
            return
        self._service.clear_ftp_log(pid)
        self.ftpLogChanged.emit()

    @Slot(str, result=QObject)
    def terminalBridgeForProfile(self, profileId: str):
        return self._service.terminal_bridge_for(profileId)

    @Slot(str, result="QVariantList")
    def ftpLogForProfile(self, profileId: str):
        return self._service.ftp_log_for(profileId)

    @Slot(str, result="QVariantMap")
    def snapshotForProfile(self, profileId: str):
        return self._service.snapshot_for(profileId)

    # ------------------------ lifecycle / dispatch ---------------------

    def dispose(self) -> None:
        self._log.info("ftp_sftp_ssh_client.viewmodel.dispose", "释放 FTP/SFTP/SSH 客户端插件 ViewModel")
        self._disposed = True
        try:
            self._uiCallback.disconnect(self._run_ui_callback)
        except (RuntimeError, TypeError):
            pass
        self._runner.shutdown(wait=False)
        self._service.close()

    def _run_background(self, fn, *, on_success=None) -> None:
        self._runner.start(
            fn,
            on_success=lambda result: self._post_ui(lambda: on_success(result) if on_success is not None else None),
            on_error=lambda exc: self._post_ui(lambda: self._handle_error(exc)),
        )

    def _emit_all_active_changed(self) -> None:
        self.connectionStateChanged.emit()
        self.localPathChanged.emit()
        self.remotePathChanged.emit()
        self.localItemsChanged.emit()
        self.remoteItemsChanged.emit()
        self.transfersChanged.emit()
        self.terminalBridgeChanged.emit()
        self.ftpLogChanged.emit()

    def _set_profiles(self, profiles: list[dict]) -> None:
        self._profiles = list(profiles)
        self.profilesChanged.emit()

    def _set_status_message(self, message: str) -> None:
        self._status_message = str(message or "")
        self.statusMessageChanged.emit()

    def _on_transfers(self, profile_id: str, items: list[dict]) -> None:
        if profile_id == self._service.active_profile_id():
            self.transfersChanged.emit()

    def _on_message(self, profile_id: str, message: str) -> None:
        if profile_id == self._service.active_profile_id():
            self._set_status_message(message)

    def _on_ftp_log(self, profile_id: str, _line: str) -> None:
        if profile_id == self._service.active_profile_id():
            self.ftpLogChanged.emit()

    def _on_snapshot_changed(self, _profile_id: str) -> None:
        self.sessionsChanged.emit()
        if _profile_id == self._service.active_profile_id():
            self.connectionStateChanged.emit()

    def _handle_error(self, exc: BaseException) -> None:
        message = str(exc)
        self._log.error(
            "ftp_sftp_ssh_client.operation.failed",
            "远程文件操作失败",
            error=message,
            activeProfileId=self._service.active_profile_id(),
        )
        self._set_status_message(message)

    def _post_ui(self, fn) -> None:
        self._uiCallback.emit(fn)

    @Slot(object)
    def _run_ui_callback(self, fn: object) -> None:
        if not self._disposed and callable(fn):
            fn()

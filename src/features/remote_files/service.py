from __future__ import annotations

from pathlib import Path
from threading import Lock

from app.logging import get_logger
from app.storage import SQLiteDatabase

from .backends import remote_target_for_rename
from .connection_pool import RemoteConnectionPool
from .models import (
    ConnectionSnapshot,
    RemoteFileItem,
    RemoteOperationResult,
    RemoteProfile,
    join_remote_path,
    parent_remote_path,
)
from .repository import RemoteProfileRepository
from .terminal_session import RemoteTerminalBridge
from .transfer_service import RemoteTransferService


class RemoteFilesService:
    def __init__(
        self,
        database: SQLiteDatabase,
        *,
        on_transfers_updated,
        on_message,
    ) -> None:
        self._log = get_logger("features.remote_files.service", plugin_id="remote-files")
        self.profiles = RemoteProfileRepository(database)
        self.pool = RemoteConnectionPool()
        self.terminal_bridge = RemoteTerminalBridge()
        self.transfers = RemoteTransferService(
            self.pool.require_backend,
            on_transfers_updated=on_transfers_updated,
            on_message=on_message,
        )
        self._state = ConnectionSnapshot()
        self._state_lock = Lock()

    def list_profiles(self) -> list[dict]:
        return [profile.to_dict() for profile in self.profiles.list_profiles()]

    def save_profile(self, payload: dict) -> list[dict]:
        profile = self.profiles.save_profile(payload)
        self._log.info(
            "remote_files.profile.saved",
            "远程连接配置已保存",
            profileId=profile.id,
            protocol=profile.protocol,
            host=profile.host,
            port=profile.port,
            jumpEnabled=profile.jump_enabled,
        )
        return self.list_profiles()

    def delete_profile(self, profile_id: str) -> list[dict]:
        self._log.info("remote_files.profile.delete_requested", "远程连接配置删除请求", profileId=profile_id)
        self.profiles.delete_profile(profile_id)
        current = self.connection_state()
        if current.get("profileId") == profile_id:
            self.disconnect()
        return self.list_profiles()

    def connection_state(self) -> dict:
        with self._state_lock:
            return self._state.to_dict()

    def connect(self, profile_id: str) -> RemoteOperationResult:
        profile = self.profiles.get_profile(profile_id)
        if profile is None:
            self._log.warning("remote_files.connect.profile_missing", "连接配置不存在", profileId=profile_id)
            raise RuntimeError("连接配置不存在")
        self._log.info(
            "remote_files.connect.start",
            "开始连接远程服务器",
            profileId=profile.id,
            protocol=profile.protocol,
            host=profile.host,
            port=profile.port,
            authKind=profile.auth_kind,
            jumpEnabled=profile.jump_enabled,
        )
        self._set_state(ConnectionSnapshot("connecting", profile.id, profile.protocol, profile.host, "连接中"))
        self.pool.connect(profile)
        self.profiles.mark_used(profile.id)
        self._set_state(ConnectionSnapshot("connected", profile.id, profile.protocol, profile.host, "已连接"))
        local_path = profile.local_root or str(Path.home())
        remote_root = (profile.remote_root or "").strip()
        if not remote_root or remote_root == "/":
            try:
                remote_root = self.pool.require_backend().home_dir() or "/"
            except Exception as exc:
                self._log.warning(
                    "remote_files.connect.home_dir_failed",
                    "读取远程家目录失败，回退到根目录",
                    profileId=profile.id,
                    error=str(exc),
                )
                remote_root = "/"
        remote_path = remote_root
        local_items = self.list_local(local_path)
        try:
            remote_items = self.list_remote(remote_path)
        except Exception as exc:
            message = f"已连接，远程目录读取失败: {exc}"
            self._set_state(ConnectionSnapshot("connected", profile.id, profile.protocol, profile.host, message))
            self._log.warning(
                "remote_files.connect.remote_list_failed",
                "连接成功但远程目录读取失败",
                profileId=profile.id,
                protocol=profile.protocol,
                host=profile.host,
                remotePath=remote_path,
                error=str(exc),
            )
            return RemoteOperationResult(
                local_items=local_items,
                remote_items=[],
                local_path=local_path,
                remote_path=remote_path,
                message=message,
            )
        self._log.info(
            "remote_files.connect.complete",
            "远程服务器连接完成",
            profileId=profile.id,
            protocol=profile.protocol,
            host=profile.host,
            localPath=local_path,
            remotePath=remote_path,
            remoteItemCount=len(remote_items),
        )
        return RemoteOperationResult(
            local_items=local_items,
            remote_items=remote_items,
            local_path=local_path,
            remote_path=remote_path,
            message="已连接",
        )

    def disconnect(self) -> None:
        current = self.connection_state()
        self._log.info("remote_files.disconnect", "断开远程连接", profileId=current.get("profileId"), host=current.get("host"))
        self.terminal_bridge.close()
        self.pool.close()
        self._set_state(ConnectionSnapshot("disconnected", "", "", "", "已断开"))

    def list_local(self, path: str) -> list[dict]:
        current = Path(path or str(Path.home())).expanduser()
        if not current.exists() or not current.is_dir():
            current = Path.home()
        items: list[RemoteFileItem] = []
        if current.parent != current:
            items.append(RemoteFileItem("..", str(current.parent), True, 0, 0, ""))
        for child in current.iterdir():
            try:
                stat_result = child.stat()
            except OSError:
                continue
            items.append(
                RemoteFileItem(
                    name=child.name,
                    path=str(child),
                    is_dir=child.is_dir(),
                    size=0 if child.is_dir() else int(stat_result.st_size),
                    modified_at=int(stat_result.st_mtime),
                )
            )
        return [item.to_dict() for item in sorted(items, key=lambda item: (not item.is_dir, item.name.lower()))]

    def list_remote(self, path: str) -> list[dict]:
        backend = self.pool.require_backend()
        current = path or "/"
        self._log.debug("remote_files.remote.list", "读取远程目录", remotePath=current)
        items = backend.list_dir(current)
        if current != "/":
            items.insert(0, RemoteFileItem("..", parent_remote_path(current), True, 0, 0, ""))
        return [item.to_dict() for item in items]

    def refresh(self, local_path: str, remote_path: str) -> RemoteOperationResult:
        self._log.info("remote_files.refresh", "刷新本地和远程目录", localPath=local_path, remotePath=remote_path)
        return RemoteOperationResult(
            local_items=self.list_local(local_path),
            remote_items=self.list_remote(remote_path),
            local_path=local_path,
            remote_path=remote_path,
        )

    def change_local_path(self, path: str) -> RemoteOperationResult:
        target = str(Path(path or str(Path.home())).expanduser())
        return RemoteOperationResult(local_items=self.list_local(target), local_path=target)

    def change_remote_path(self, path: str) -> RemoteOperationResult:
        target = path or "/"
        self._log.info("remote_files.remote.change_path", "切换远程目录", remotePath=target)
        return RemoteOperationResult(remote_items=self.list_remote(target), remote_path=target)

    def upload(self, local_paths: list[str], remote_dir: str) -> list[str]:
        self._log.info("remote_files.upload.requested", "上传请求", fileCount=len(local_paths), remotePath=remote_dir)
        transfer_ids: list[str] = []
        for local_path in local_paths:
            path = Path(local_path)
            if not path.is_file():
                continue
            transfer_ids.append(self.transfers.start_upload(str(path), join_remote_path(remote_dir, path.name)))
        return transfer_ids

    def upload_paths(self, local_paths: list[str], remote_dir: str) -> list[str]:
        """Upload arbitrary local paths to ``remote_dir``.

        Files are queued directly; directories are walked recursively, creating
        matching remote directories before queueing each contained file.
        """

        self._log.info(
            "remote_files.upload_paths.requested",
            "上传路径请求",
            pathCount=len(local_paths),
            remotePath=remote_dir,
        )
        backend = self.pool.require_backend()
        transfer_ids: list[str] = []
        for raw in local_paths:
            path = Path(str(raw or "")).expanduser()
            if not path.exists():
                continue
            if path.is_file():
                transfer_ids.append(
                    self.transfers.start_upload(str(path), join_remote_path(remote_dir, path.name))
                )
                continue
            if not path.is_dir():
                continue
            root_remote = join_remote_path(remote_dir, path.name)
            self._ensure_remote_dir(backend, root_remote)
            for child in sorted(path.rglob("*")):
                rel_parts = child.relative_to(path).parts
                remote_child = root_remote
                for part in rel_parts:
                    remote_child = join_remote_path(remote_child, part)
                if child.is_dir():
                    self._ensure_remote_dir(backend, remote_child)
                elif child.is_file():
                    transfer_ids.append(self.transfers.start_upload(str(child), remote_child))
        return transfer_ids

    def _ensure_remote_dir(self, backend, remote_path: str) -> None:
        try:
            backend.mkdir(remote_path)
        except Exception as exc:
            self._log.debug(
                "remote_files.remote.mkdir_skipped",
                "远程目录创建已跳过(可能已存在)",
                remotePath=remote_path,
                error=str(exc),
            )

    def download(self, remote_items: list[dict], local_dir: str) -> list[str]:
        self._log.info("remote_files.download.requested", "下载请求", itemCount=len(remote_items), localPath=local_dir)
        transfer_ids: list[str] = []
        for item in remote_items:
            if item.get("isDir"):
                continue
            name = str(item.get("name") or Path(str(item.get("path") or "")).name)
            remote_path = str(item.get("path") or "")
            if not remote_path:
                continue
            local_path = str(Path(local_dir or str(Path.home())) / name)
            transfer_ids.append(self.transfers.start_download(remote_path, local_path, int(item.get("size") or 0)))
        return transfer_ids

    def download_to(self, remote_items: list[dict], target_dir: str) -> list[str]:
        target = str(Path(target_dir or str(Path.home())).expanduser())
        Path(target).mkdir(parents=True, exist_ok=True)
        self._log.info(
            "remote_files.download_to.requested",
            "下载到指定目录请求",
            itemCount=len(remote_items),
            targetDir=target,
        )
        return self.download(remote_items, target)

    def mkdir_remote(self, path: str) -> None:
        self._log.info("remote_files.remote.mkdir", "创建远程目录", remotePath=path)
        self.pool.require_backend().mkdir(path)

    def rename_remote(self, source: str, new_name: str) -> None:
        if not new_name.strip():
            return
        target = remote_target_for_rename(source, new_name.strip())
        self._log.info("remote_files.remote.rename", "重命名远程项目", remotePath=source, targetPath=target)
        self.pool.require_backend().rename(source, target)

    def delete_remote(self, items: list[dict]) -> None:
        self._log.info("remote_files.remote.delete", "删除远程项目", itemCount=len(items))
        backend = self.pool.require_backend()
        for item in items:
            path = str(item.get("path") or "")
            if not path or path == "/":
                continue
            if bool(item.get("isDir")):
                backend.delete_dir(path)
            else:
                backend.delete_file(path)

    def open_terminal(self) -> None:
        backend = self.pool.require_backend()
        profile = self.pool.profile
        if profile is None or profile.protocol != "sftp":
            self._log.warning("remote_files.terminal.unsupported", "当前连接不支持 SSH 终端")
            raise RuntimeError("只有 SFTP 连接支持 SSH 终端")
        self._log.info("remote_files.terminal.open", "打开 SSH 终端", profileId=profile.id, host=profile.host)
        self.terminal_bridge.attach(backend.open_terminal())

    def close(self) -> None:
        self.transfers.close()
        self.disconnect()

    def _set_state(self, state: ConnectionSnapshot) -> None:
        with self._state_lock:
            self._state = state

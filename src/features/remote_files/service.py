from __future__ import annotations

from pathlib import Path

from app.logging import get_logger
from app.storage import SQLiteDatabase

from .backends import create_backend, remote_target_for_rename
from .connection_pool import RemoteConnectionPool
from .models import (
    ConnectionSnapshot,
    RemoteFileItem,
    RemoteOperationResult,
    join_remote_path,
    parent_remote_path,
)
from .repository import RemoteProfileRepository
from .session import RemoteSession


class RemoteFilesService:
    """Session-aware orchestrator.

    The pool holds zero or more live sessions keyed by profile id; the
    "active" session is whichever profile the user is currently viewing.
    Every public method takes an optional ``profile_id`` and defaults to
    the active session so existing single-session call sites keep working.
    """

    def __init__(
        self,
        database: SQLiteDatabase,
        *,
        on_transfers_updated,
        on_message,
        on_ftp_log=None,
        on_snapshot_changed=None,
    ) -> None:
        self._log = get_logger("features.remote_files.service", plugin_id="remote-files")
        self.profiles = RemoteProfileRepository(database)
        self.pool = RemoteConnectionPool()
        self._active_id: str = ""

        self._on_transfers_updated = on_transfers_updated
        self._on_message = on_message
        self._on_ftp_log = on_ftp_log
        self._on_snapshot_changed = on_snapshot_changed

    # ------------------------- session helpers -------------------------

    def active_profile_id(self) -> str:
        return self._active_id

    def set_active(self, profile_id: str) -> None:
        self._active_id = profile_id or ""

    def _resolve_id(self, profile_id: str | None) -> str:
        return profile_id if profile_id else self._active_id

    def active_session(self) -> RemoteSession | None:
        if not self._active_id:
            return None
        return self.pool.get(self._active_id)

    def has_session(self, profile_id: str) -> bool:
        return self.pool.has(profile_id)

    def sessions_summary(self) -> list[dict]:
        return [session.snapshot() for session in self.pool.list_sessions()]

    def terminal_bridge_for(self, profile_id: str):
        session = self.pool.get(profile_id)
        return session.terminal_bridge if session is not None else None

    def ftp_log_for(self, profile_id: str) -> list[str]:
        session = self.pool.get(profile_id)
        return session.ftp_log_snapshot() if session is not None else []

    def clear_ftp_log(self, profile_id: str) -> None:
        session = self.pool.get(profile_id)
        if session is not None:
            session.clear_ftp_log()

    def transfers_for(self, profile_id: str) -> list[dict]:
        session = self.pool.get(profile_id)
        return session.transfers.items() if session is not None else []

    def remote_path_for(self, profile_id: str) -> str:
        session = self.pool.get(profile_id)
        return session.remote_path if session is not None else ""

    def local_path_for(self, profile_id: str) -> str:
        session = self.pool.get(profile_id)
        return session.local_path if session is not None else ""

    def remote_items_for(self, profile_id: str) -> list[dict]:
        session = self.pool.get(profile_id)
        return session.remote_items if session is not None else []

    def local_items_for(self, profile_id: str) -> list[dict]:
        session = self.pool.get(profile_id)
        return session.local_items if session is not None else []

    def snapshot_for(self, profile_id: str) -> dict:
        session = self.pool.get(profile_id)
        if session is not None:
            return session.snapshot()
        return ConnectionSnapshot(profile_id=profile_id).to_dict()

    # --------------------------- profile CRUD --------------------------

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
        if self.pool.has(profile_id):
            self.disconnect(profile_id)
        return self.list_profiles()

    # --------------------------- connect / disconnect ------------------

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
        backend = create_backend(profile)
        session = RemoteSession(
            profile,
            backend,
            on_transfers_updated=self._on_transfers_updated,
            on_message=self._on_message,
            on_ftp_log=self._on_ftp_log,
            on_snapshot_changed=self._on_snapshot_changed,
        )
        if profile.protocol in {"ftp", "ftps"} and hasattr(backend, "set_log_sink"):
            backend.set_log_sink(session.append_ftp_log)
        self.pool.add(session)
        try:
            backend.connect()
        except Exception:
            self.pool.close_session(profile.id)
            raise
        self.profiles.mark_used(profile.id)
        session.update_snapshot(status="connected", message="已连接")

        local_path = profile.local_root or str(Path.home())
        remote_root = (profile.remote_root or "").strip()
        if not remote_root or remote_root == "/":
            try:
                remote_root = backend.home_dir() or "/"
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
        session.local_path = local_path
        session.local_items = local_items
        try:
            remote_items = self.list_remote(profile.id, remote_path)
        except Exception as exc:
            message = f"已连接，远程目录读取失败: {exc}"
            session.update_snapshot(status="connected", message=message)
            self._log.warning(
                "remote_files.connect.remote_list_failed",
                "连接成功但远程目录读取失败",
                profileId=profile.id,
                protocol=profile.protocol,
                host=profile.host,
                remotePath=remote_path,
                error=str(exc),
            )
            session.remote_path = remote_path
            session.remote_items = []
            return RemoteOperationResult(
                local_items=local_items,
                remote_items=[],
                local_path=local_path,
                remote_path=remote_path,
                message=message,
            )
        session.remote_path = remote_path
        session.remote_items = remote_items
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

    def disconnect(self, profile_id: str | None = None) -> str:
        target = self._resolve_id(profile_id)
        if not target:
            return ""
        self._log.info("remote_files.disconnect", "断开远程连接", profileId=target)
        self.pool.close_session(target)
        if self._active_id == target:
            remaining = self.pool.list_sessions()
            self._active_id = remaining[0].profile_id if remaining else ""
        return target

    # --------------------------- listings ------------------------------

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

    def list_remote(self, profile_id: str, path: str) -> list[dict]:
        session = self.pool.require(profile_id)
        current = path or "/"
        self._log.debug("remote_files.remote.list", "读取远程目录", profileId=profile_id, remotePath=current)
        items = session.backend.list_dir(current)
        if current != "/":
            items.insert(0, RemoteFileItem("..", parent_remote_path(current), True, 0, 0, ""))
        return [item.to_dict() for item in items]

    def refresh(self, profile_id: str | None, local_path: str, remote_path: str) -> RemoteOperationResult:
        target = self._resolve_id(profile_id)
        self._log.info("remote_files.refresh", "刷新本地和远程目录", profileId=target, localPath=local_path, remotePath=remote_path)
        local_items = self.list_local(local_path)
        remote_items = self.list_remote(target, remote_path)
        session = self.pool.get(target)
        if session is not None:
            session.local_items = local_items
            session.remote_items = remote_items
            session.local_path = local_path
            session.remote_path = remote_path
        return RemoteOperationResult(
            local_items=local_items,
            remote_items=remote_items,
            local_path=local_path,
            remote_path=remote_path,
        )

    def change_local_path(self, profile_id: str | None, path: str) -> RemoteOperationResult:
        target = self._resolve_id(profile_id)
        resolved = str(Path(path or str(Path.home())).expanduser())
        items = self.list_local(resolved)
        session = self.pool.get(target)
        if session is not None:
            session.local_path = resolved
            session.local_items = items
        return RemoteOperationResult(local_items=items, local_path=resolved)

    def change_remote_path(self, profile_id: str | None, path: str) -> RemoteOperationResult:
        target = self._resolve_id(profile_id)
        resolved = path or "/"
        self._log.info("remote_files.remote.change_path", "切换远程目录", profileId=target, remotePath=resolved)
        items = self.list_remote(target, resolved)
        session = self.pool.get(target)
        if session is not None:
            session.remote_path = resolved
            session.remote_items = items
        return RemoteOperationResult(remote_items=items, remote_path=resolved)

    # --------------------------- transfers -----------------------------

    def upload(self, profile_id: str | None, local_paths: list[str], remote_dir: str) -> list[str]:
        target = self._resolve_id(profile_id)
        session = self.pool.require(target)
        self._log.info("remote_files.upload.requested", "上传请求", profileId=target, fileCount=len(local_paths), remotePath=remote_dir)
        transfer_ids: list[str] = []
        for local_path in local_paths:
            path = Path(local_path)
            if not path.is_file():
                continue
            transfer_ids.append(session.transfers.start_upload(str(path), join_remote_path(remote_dir, path.name)))
        return transfer_ids

    def upload_paths(self, profile_id: str | None, local_paths: list[str], remote_dir: str) -> list[str]:
        target = self._resolve_id(profile_id)
        session = self.pool.require(target)
        self._log.info(
            "remote_files.upload_paths.requested",
            "上传路径请求",
            profileId=target,
            pathCount=len(local_paths),
            remotePath=remote_dir,
        )
        transfer_ids: list[str] = []
        for raw in local_paths:
            path = Path(str(raw or "")).expanduser()
            if not path.exists():
                continue
            if path.is_file():
                transfer_ids.append(
                    session.transfers.start_upload(str(path), join_remote_path(remote_dir, path.name))
                )
                continue
            if not path.is_dir():
                continue
            root_remote = join_remote_path(remote_dir, path.name)
            self._ensure_remote_dir(session.backend, root_remote)
            for child in sorted(path.rglob("*")):
                rel_parts = child.relative_to(path).parts
                remote_child = root_remote
                for part in rel_parts:
                    remote_child = join_remote_path(remote_child, part)
                if child.is_dir():
                    self._ensure_remote_dir(session.backend, remote_child)
                elif child.is_file():
                    transfer_ids.append(session.transfers.start_upload(str(child), remote_child))
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

    def download(self, profile_id: str | None, remote_items: list[dict], local_dir: str) -> list[str]:
        target = self._resolve_id(profile_id)
        session = self.pool.require(target)
        self._log.info("remote_files.download.requested", "下载请求", profileId=target, itemCount=len(remote_items), localPath=local_dir)
        transfer_ids: list[str] = []
        for item in remote_items:
            if item.get("isDir"):
                continue
            name = str(item.get("name") or Path(str(item.get("path") or "")).name)
            remote_path = str(item.get("path") or "")
            if not remote_path:
                continue
            local_path = str(Path(local_dir or str(Path.home())) / name)
            transfer_ids.append(session.transfers.start_download(remote_path, local_path, int(item.get("size") or 0)))
        return transfer_ids

    def download_to(self, profile_id: str | None, remote_items: list[dict], target_dir: str) -> list[str]:
        target = str(Path(target_dir or str(Path.home())).expanduser())
        Path(target).mkdir(parents=True, exist_ok=True)
        self._log.info(
            "remote_files.download_to.requested",
            "下载到指定目录请求",
            itemCount=len(remote_items),
            targetDir=target,
        )
        return self.download(profile_id, remote_items, target)

    def cancel_transfer(self, profile_id: str | None, transfer_id: str) -> None:
        target = self._resolve_id(profile_id)
        session = self.pool.get(target)
        if session is not None:
            session.transfers.cancel(transfer_id)

    def clear_finished_transfers(self, profile_id: str | None) -> None:
        target = self._resolve_id(profile_id)
        session = self.pool.get(target)
        if session is not None:
            session.transfers.clear_finished()

    # --------------------------- remote mutations ----------------------

    def mkdir_remote(self, profile_id: str | None, path: str) -> None:
        target = self._resolve_id(profile_id)
        session = self.pool.require(target)
        self._log.info("remote_files.remote.mkdir", "创建远程目录", profileId=target, remotePath=path)
        session.backend.mkdir(path)

    def rename_remote(self, profile_id: str | None, source: str, new_name: str) -> None:
        if not new_name.strip():
            return
        target = self._resolve_id(profile_id)
        session = self.pool.require(target)
        renamed = remote_target_for_rename(source, new_name.strip())
        self._log.info("remote_files.remote.rename", "重命名远程项目", profileId=target, remotePath=source, targetPath=renamed)
        session.backend.rename(source, renamed)

    def delete_remote(self, profile_id: str | None, items: list[dict]) -> None:
        target = self._resolve_id(profile_id)
        session = self.pool.require(target)
        self._log.info("remote_files.remote.delete", "删除远程项目", profileId=target, itemCount=len(items))
        for item in items:
            path = str(item.get("path") or "")
            if not path or path == "/":
                continue
            if bool(item.get("isDir")):
                session.backend.delete_dir(path)
            else:
                session.backend.delete_file(path)

    # --------------------------- terminal ------------------------------

    def open_terminal(self, profile_id: str | None = None) -> None:
        target = self._resolve_id(profile_id)
        session = self.pool.require(target)
        if session.profile.protocol != "sftp":
            self._log.warning("remote_files.terminal.unsupported", "当前连接不支持 SSH 终端", profileId=target)
            raise RuntimeError("只有 SFTP 连接支持 SSH 终端")
        self._log.info("remote_files.terminal.open", "打开 SSH 终端", profileId=target, host=session.profile.host)
        session.terminal_bridge.attach(session.backend.open_terminal())

    def close_terminal(self, profile_id: str | None = None) -> None:
        target = self._resolve_id(profile_id)
        session = self.pool.get(target)
        if session is not None and session.has_terminal_bridge():
            session.terminal_bridge.close()

    def close(self) -> None:
        self.pool.close_all()
        self._active_id = ""

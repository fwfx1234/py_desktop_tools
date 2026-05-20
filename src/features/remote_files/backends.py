from __future__ import annotations

from pathlib import Path, PurePosixPath
import stat
from threading import RLock
import time
from typing import Callable, Protocol

from app.logging import get_logger

from .models import RemoteFileItem, RemoteProfile, join_remote_path, parent_remote_path


ProgressCallback = Callable[[int, int], None]
_LOG = None


def _logger():
    global _LOG
    if _LOG is None:
        _LOG = get_logger("features.remote_files.backends", plugin_id="remote-files")
    return _LOG


class RemoteBackend(Protocol):
    profile: RemoteProfile

    def connect(self) -> None:
        ...

    def close(self) -> None:
        ...

    def list_dir(self, path: str) -> list[RemoteFileItem]:
        ...

    def mkdir(self, path: str) -> None:
        ...

    def rename(self, source: str, target: str) -> None:
        ...

    def delete_file(self, path: str) -> None:
        ...

    def delete_dir(self, path: str) -> None:
        ...

    def upload_file(self, local_path: str, remote_path: str, progress: ProgressCallback | None = None) -> None:
        ...

    def download_file(self, remote_path: str, local_path: str, progress: ProgressCallback | None = None) -> None:
        ...

    def open_terminal(self):
        ...

    def home_dir(self) -> str:
        ...


class SftpBackend:
    def __init__(self, profile: RemoteProfile, *, ssh_client_factory=None) -> None:
        self.profile = profile
        self._ssh_client_factory = ssh_client_factory
        self._ssh = None
        self._jump_ssh = None
        self._transport = None

    def connect(self) -> None:
        paramiko = _paramiko()
        factory = self._ssh_client_factory or paramiko.SSHClient
        sock = None
        if self.profile.jump_enabled:
            _logger().info(
                "remote_files.sftp.jump.connect_start",
                "开始连接 SFTP 跳板机",
                host=self.profile.jump_host,
                port=self.profile.jump_port,
                username=self.profile.jump_username or self.profile.username,
            )
            self._jump_ssh = factory()
            self._prepare_client(self._jump_ssh, paramiko)
            self._connect_client(
                self._jump_ssh,
                host=self.profile.jump_host,
                port=self.profile.jump_port,
                username=self.profile.jump_username or self.profile.username,
                password=self.profile.jump_password,
                key_path=self.profile.jump_private_key_path,
                passphrase=self.profile.jump_private_key_passphrase,
                use_agent=not bool(self.profile.jump_password or self.profile.jump_private_key_path),
            )
            jump_transport = self._jump_ssh.get_transport()
            if jump_transport is None:
                _logger().error("remote_files.sftp.jump.transport_missing", "跳板机 SSH transport 不可用", host=self.profile.jump_host)
                raise RuntimeError("跳板机 SSH transport 不可用")
            sock = jump_transport.open_channel(
                "direct-tcpip",
                (self.profile.host, self.profile.port),
                ("127.0.0.1", 0),
            )
            _logger().info(
                "remote_files.sftp.jump.connect_complete",
                "SFTP 跳板机连接完成",
                host=self.profile.jump_host,
                targetHost=self.profile.host,
                targetPort=self.profile.port,
            )

        _logger().info(
            "remote_files.sftp.connect_start",
            "开始连接 SFTP 目标服务器",
            host=self.profile.host,
            port=self.profile.port,
            username=self.profile.username,
            authKind=self.profile.auth_kind,
            viaJump=bool(sock),
        )
        self._ssh = factory()
        self._prepare_client(self._ssh, paramiko)
        self._connect_client(
            self._ssh,
            host=self.profile.host,
            port=self.profile.port,
            username=self.profile.username,
            password=self.profile.password,
            key_path=self.profile.private_key_path,
            passphrase=self.profile.private_key_passphrase,
            use_agent=self.profile.auth_kind == "agent",
            sock=sock,
        )
        self._transport = self._ssh.get_transport()
        if self._transport is None:
            _logger().error("remote_files.sftp.transport_missing", "SSH transport 不可用", host=self.profile.host)
            raise RuntimeError("SSH transport 不可用")
        _logger().info("remote_files.sftp.connect_complete", "SFTP 目标服务器连接完成", host=self.profile.host, port=self.profile.port)

    def close(self) -> None:
        _logger().info("remote_files.sftp.close", "关闭 SFTP 连接", host=self.profile.host)
        for client in (self._ssh, self._jump_ssh):
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass
        self._ssh = None
        self._jump_ssh = None
        self._transport = None

    def list_dir(self, path: str) -> list[RemoteFileItem]:
        _logger().debug("remote_files.sftp.list_dir", "读取 SFTP 目录", host=self.profile.host, remotePath=path)
        sftp = self._open_sftp()
        try:
            items: list[RemoteFileItem] = []
            for attr in sftp.listdir_attr(path):
                name = attr.filename
                if name in {".", ".."}:
                    continue
                mode = int(getattr(attr, "st_mode", 0) or 0)
                items.append(
                    RemoteFileItem(
                        name=name,
                        path=join_remote_path(path, name),
                        is_dir=stat.S_ISDIR(mode),
                        size=int(getattr(attr, "st_size", 0) or 0),
                        modified_at=int(getattr(attr, "st_mtime", 0) or 0),
                        permissions=stat.filemode(mode) if mode else "",
                    )
                )
            return sorted(items, key=lambda item: (not item.is_dir, item.name.lower()))
        finally:
            _close_quietly(sftp)

    def mkdir(self, path: str) -> None:
        _logger().info("remote_files.sftp.mkdir", "创建 SFTP 目录", host=self.profile.host, remotePath=path)
        sftp = self._open_sftp()
        try:
            sftp.mkdir(path)
        finally:
            _close_quietly(sftp)

    def rename(self, source: str, target: str) -> None:
        _logger().info("remote_files.sftp.rename", "重命名 SFTP 项目", host=self.profile.host, remotePath=source, targetPath=target)
        sftp = self._open_sftp()
        try:
            sftp.rename(source, target)
        finally:
            _close_quietly(sftp)

    def delete_file(self, path: str) -> None:
        _logger().info("remote_files.sftp.delete_file", "删除 SFTP 文件", host=self.profile.host, remotePath=path)
        sftp = self._open_sftp()
        try:
            sftp.remove(path)
        finally:
            _close_quietly(sftp)

    def delete_dir(self, path: str) -> None:
        _logger().info("remote_files.sftp.delete_dir", "删除 SFTP 目录", host=self.profile.host, remotePath=path)
        sftp = self._open_sftp()
        try:
            sftp.rmdir(path)
        finally:
            _close_quietly(sftp)

    def upload_file(self, local_path: str, remote_path: str, progress: ProgressCallback | None = None) -> None:
        _logger().info("remote_files.sftp.upload", "上传 SFTP 文件", host=self.profile.host, localPath=local_path, remotePath=remote_path)
        sftp = self._open_sftp()
        try:
            sftp.put(local_path, remote_path, callback=progress)
        finally:
            _close_quietly(sftp)

    def download_file(self, remote_path: str, local_path: str, progress: ProgressCallback | None = None) -> None:
        _logger().info("remote_files.sftp.download", "下载 SFTP 文件", host=self.profile.host, remotePath=remote_path, localPath=local_path)
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        sftp = self._open_sftp()
        try:
            sftp.get(remote_path, local_path, callback=progress)
        finally:
            _close_quietly(sftp)

    def open_terminal(self):
        if self._ssh is None:
            raise RuntimeError("SFTP 连接未建立")
        _logger().info("remote_files.sftp.terminal.open", "打开 SFTP 共享 SSH 终端", host=self.profile.host)
        return self._ssh.invoke_shell(term="xterm-256color")

    def home_dir(self) -> str:
        sftp = self._open_sftp()
        try:
            try:
                home = sftp.normalize(".")
            except Exception:
                home = "/"
            return home if home and home.startswith("/") else "/"
        finally:
            _close_quietly(sftp)

    def _open_sftp(self):
        if self._transport is None:
            raise RuntimeError("SFTP 连接未建立")
        paramiko = _paramiko()
        return paramiko.SFTPClient.from_transport(self._transport)

    @staticmethod
    def _prepare_client(client, paramiko) -> None:
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def _connect_client(
        self,
        client,
        *,
        host: str,
        port: int,
        username: str,
        password: str = "",
        key_path: str = "",
        passphrase: str = "",
        use_agent: bool = False,
        sock=None,
    ) -> None:
        kwargs = {
            "hostname": host,
            "port": int(port),
            "username": username or None,
            "timeout": self.profile.connect_timeout,
            "banner_timeout": self.profile.connect_timeout,
            "auth_timeout": self.profile.connect_timeout,
            "sock": sock,
            "look_for_keys": use_agent,
            "allow_agent": use_agent,
        }
        if key_path:
            kwargs["key_filename"] = key_path
            kwargs["passphrase"] = passphrase or None
        elif password:
            kwargs["password"] = password
        client.connect(**kwargs)


class FtpBackend:
    def __init__(self, profile: RemoteProfile, *, ftp_factory=None, ftps_factory=None) -> None:
        self.profile = profile
        self._ftp_factory = ftp_factory
        self._ftps_factory = ftps_factory
        self._ftp = None
        self._lock = RLock()

    def connect(self) -> None:
        import ftplib

        with self._lock:
            factory = self._ftps_factory if self.profile.protocol == "ftps" else self._ftp_factory
            factory = factory or (ftplib.FTP_TLS if self.profile.protocol == "ftps" else ftplib.FTP)
            _logger().info(
                "remote_files.ftp.connect_start",
                "开始连接 FTP/FTPS 服务器",
                protocol=self.profile.protocol,
                host=self.profile.host,
                port=self.profile.port,
                username=self.profile.username,
            )
            self._ftp = factory()
            if self.profile.encoding:
                self._ftp.encoding = self.profile.encoding
            self._ftp.connect(self.profile.host, self.profile.port, timeout=self.profile.connect_timeout)
            self._ftp.login(self.profile.username, self.profile.password)
            self._ftp.set_pasv(self.profile.passive_mode)
            if self.profile.protocol == "ftps" and hasattr(self._ftp, "prot_p"):
                self._ftp.prot_p()
            _logger().info(
                "remote_files.ftp.connect_complete",
                "FTP/FTPS 服务器连接完成",
                protocol=self.profile.protocol,
                host=self.profile.host,
                port=self.profile.port,
                passiveMode=self.profile.passive_mode,
            )

    def close(self) -> None:
        _logger().info("remote_files.ftp.close", "关闭 FTP/FTPS 连接", protocol=self.profile.protocol, host=self.profile.host)
        with self._lock:
            ftp = self._ftp
            self._ftp = None
        if ftp is None:
            return
        try:
            ftp.quit()
        except Exception:
            try:
                ftp.close()
            except Exception:
                pass

    def list_dir(self, path: str) -> list[RemoteFileItem]:
        with self._lock:
            ftp = self._require_ftp()
            try:
                _logger().debug("remote_files.ftp.list_mlsd", "使用 MLSD 读取 FTP/FTPS 目录", protocol=self.profile.protocol, host=self.profile.host, remotePath=path)
                entries = list(ftp.mlsd(path))
                return sorted(
                    [self._item_from_mlsd(path, name, facts) for name, facts in entries if name not in {".", ".."}],
                    key=lambda item: (not item.is_dir, item.name.lower()),
                )
            except Exception as exc:
                _logger().warning(
                    "remote_files.ftp.list_mlsd_failed",
                    "MLSD 读取失败，切换到 NLST fallback",
                    protocol=self.profile.protocol,
                    host=self.profile.host,
                    remotePath=path,
                    error=str(exc),
                )
                names = ftp.nlst(path)
                items: list[RemoteFileItem] = []
                for raw_name in names:
                    name = str(raw_name).rstrip("/").rsplit("/", 1)[-1]
                    if name in {".", "..", ""}:
                        continue
                    remote_path = join_remote_path(path, name)
                    is_dir = self._is_dir(remote_path)
                    items.append(
                        RemoteFileItem(
                            name=name,
                            path=remote_path,
                            is_dir=is_dir,
                            size=0 if is_dir else self._size(remote_path),
                            modified_at=self._modified_at(remote_path),
                        )
                    )
                return sorted(items, key=lambda item: (not item.is_dir, item.name.lower()))

    def mkdir(self, path: str) -> None:
        with self._lock:
            _logger().info("remote_files.ftp.mkdir", "创建 FTP/FTPS 目录", protocol=self.profile.protocol, host=self.profile.host, remotePath=path)
            self._require_ftp().mkd(path)

    def rename(self, source: str, target: str) -> None:
        with self._lock:
            _logger().info("remote_files.ftp.rename", "重命名 FTP/FTPS 项目", protocol=self.profile.protocol, host=self.profile.host, remotePath=source, targetPath=target)
            self._require_ftp().rename(source, target)

    def delete_file(self, path: str) -> None:
        with self._lock:
            _logger().info("remote_files.ftp.delete_file", "删除 FTP/FTPS 文件", protocol=self.profile.protocol, host=self.profile.host, remotePath=path)
            self._require_ftp().delete(path)

    def delete_dir(self, path: str) -> None:
        with self._lock:
            _logger().info("remote_files.ftp.delete_dir", "删除 FTP/FTPS 目录", protocol=self.profile.protocol, host=self.profile.host, remotePath=path)
            self._require_ftp().rmd(path)

    def upload_file(self, local_path: str, remote_path: str, progress: ProgressCallback | None = None) -> None:
        with self._lock:
            _logger().info("remote_files.ftp.upload", "上传 FTP/FTPS 文件", protocol=self.profile.protocol, host=self.profile.host, localPath=local_path, remotePath=remote_path)
            ftp = self._require_ftp()
            total = Path(local_path).stat().st_size
            sent = 0

            def callback(block: bytes) -> None:
                nonlocal sent
                sent += len(block)
                if progress is not None:
                    progress(sent, total)

            with Path(local_path).open("rb") as file_obj:
                ftp.storbinary(f"STOR {remote_path}", file_obj, blocksize=64 * 1024, callback=callback)

    def download_file(self, remote_path: str, local_path: str, progress: ProgressCallback | None = None) -> None:
        with self._lock:
            _logger().info("remote_files.ftp.download", "下载 FTP/FTPS 文件", protocol=self.profile.protocol, host=self.profile.host, remotePath=remote_path, localPath=local_path)
            ftp = self._require_ftp()
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            total = self._size(remote_path)
            received = 0
            with Path(local_path).open("wb") as file_obj:

                def callback(block: bytes) -> None:
                    nonlocal received
                    file_obj.write(block)
                    received += len(block)
                    if progress is not None:
                        progress(received, total)

                ftp.retrbinary(f"RETR {remote_path}", callback, blocksize=64 * 1024)

    def open_terminal(self):
        raise RuntimeError("FTP/FTPS 不支持 SSH 终端")

    def home_dir(self) -> str:
        with self._lock:
            try:
                value = str(self._require_ftp().pwd() or "/")
            except Exception:
                value = "/"
            if not value.startswith("/"):
                value = "/" + value
            return value

    def _require_ftp(self):
        if self._ftp is None:
            raise RuntimeError("FTP 连接未建立")
        return self._ftp

    def _item_from_mlsd(self, path: str, name: str, facts: dict) -> RemoteFileItem:
        item_type = str(facts.get("type") or "").lower()
        return RemoteFileItem(
            name=name,
            path=join_remote_path(path, name),
            is_dir=item_type == "dir",
            size=_safe_int(facts.get("size"), 0),
            modified_at=_parse_ftp_modify(facts.get("modify")),
            permissions=str(facts.get("perm") or ""),
        )

    def _is_dir(self, path: str) -> bool:
        ftp = self._require_ftp()
        current = ""
        try:
            current = ftp.pwd()
            ftp.cwd(path)
            return True
        except Exception:
            return False
        finally:
            if current:
                try:
                    ftp.cwd(current)
                except Exception:
                    pass

    def _size(self, path: str) -> int:
        try:
            return int(self._require_ftp().size(path) or 0)
        except Exception:
            return 0

    def _modified_at(self, path: str) -> int:
        try:
            response = str(self._require_ftp().sendcmd(f"MDTM {path}") or "")
            return _parse_ftp_modify(response.split(maxsplit=1)[1] if " " in response else response)
        except Exception:
            return 0


def create_backend(profile: RemoteProfile) -> RemoteBackend:
    if profile.protocol == "sftp":
        return SftpBackend(profile)
    return FtpBackend(profile)


def remote_target_for_rename(source: str, new_name: str) -> str:
    return join_remote_path(parent_remote_path(source), new_name)


def _paramiko():
    import paramiko

    return paramiko


def _close_quietly(obj) -> None:
    try:
        obj.close()
    except Exception:
        pass


def _safe_int(value: object, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _parse_ftp_modify(value: object) -> int:
    text = str(value or "").strip()
    if len(text) < 14:
        return 0
    try:
        return int(time.mktime(time.strptime(text[:14], "%Y%m%d%H%M%S")))
    except ValueError:
        return 0

from __future__ import annotations

from pathlib import Path

from features.remote_files.backends import FtpBackend, SftpBackend
from features.remote_files.models import RemoteProfile


class FakeTransport:
    def __init__(self) -> None:
        self.opened_channels = []

    def open_channel(self, kind, destination, source):
        self.opened_channels.append((kind, destination, source))
        return "jump-socket"


class FakeShell:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeSSHClient:
    instances = []

    def __init__(self) -> None:
        self.transport = FakeTransport()
        self.connect_kwargs = None
        self.shell = FakeShell()
        FakeSSHClient.instances.append(self)

    def load_system_host_keys(self) -> None:
        pass

    def set_missing_host_key_policy(self, policy) -> None:
        self.policy = policy

    def connect(self, **kwargs) -> None:
        self.connect_kwargs = kwargs

    def get_transport(self):
        return self.transport

    def invoke_shell(self, **kwargs):
        self.shell_kwargs = kwargs
        return self.shell

    def close(self) -> None:
        self.closed = True


class FakeFTP:
    def __init__(self) -> None:
        self.commands = []
        self.encoding = ""
        self.cwd_path = "/"
        self.files = {"/remote/a.txt": b"abc"}

    def connect(self, host, port, timeout):
        self.commands.append(("connect", host, port, timeout))

    def login(self, username, password):
        self.commands.append(("login", username, password))

    def set_pasv(self, passive):
        self.commands.append(("pasv", passive))

    def mlsd(self, path):
        raise RuntimeError("mlsd unsupported")

    def nlst(self, path):
        return [f"{path.rstrip('/')}/a.txt", f"{path.rstrip('/')}/dir"]

    def pwd(self):
        return self.cwd_path

    def cwd(self, path):
        if path.endswith("/dir"):
            self.cwd_path = path
            return
        raise RuntimeError("not dir")

    def size(self, path):
        return len(self.files.get(path, b""))

    def sendcmd(self, command):
        return "213 20250102030405"

    def mkd(self, path):
        self.commands.append(("mkd", path))

    def rename(self, source, target):
        self.commands.append(("rename", source, target))

    def delete(self, path):
        self.commands.append(("delete", path))

    def rmd(self, path):
        self.commands.append(("rmd", path))

    def storbinary(self, command, file_obj, blocksize, callback):
        block = file_obj.read()
        callback(block)
        self.commands.append(("stor", command, block))

    def retrbinary(self, command, callback, blocksize):
        callback(b"abc")
        self.commands.append(("retr", command))

    def quit(self):
        self.commands.append(("quit",))


def test_sftp_backend_uses_jump_host_direct_tcpip(monkeypatch) -> None:
    class FakeParamiko:
        SSHClient = FakeSSHClient

        class AutoAddPolicy:
            pass

        class SFTPClient:
            @staticmethod
            def from_transport(transport):
                return object()

    FakeSSHClient.instances = []
    monkeypatch.setattr("features.remote_files.backends._paramiko", lambda: FakeParamiko)
    profile = RemoteProfile(
        protocol="sftp",
        host="target.example.com",
        username="alice",
        password="secret",
        jump_enabled=True,
        jump_host="jump.example.com",
        jump_username="jump",
        jump_password="jump-secret",
    )

    backend = SftpBackend(profile, ssh_client_factory=FakeSSHClient)
    backend.connect()
    shell = backend.open_terminal()

    jump_client, target_client = FakeSSHClient.instances
    assert jump_client.connect_kwargs["hostname"] == "jump.example.com"
    assert jump_client.transport.opened_channels[0][0] == "direct-tcpip"
    assert jump_client.transport.opened_channels[0][1] == ("target.example.com", 22)
    assert target_client.connect_kwargs["sock"] == "jump-socket"
    assert target_client.shell_kwargs["term"] == "xterm-256color"
    assert shell is target_client.shell


def test_ftp_backend_lists_with_nlst_fallback_and_transfers(tmp_path: Path) -> None:
    ftp = FakeFTP()
    profile = RemoteProfile(protocol="ftp", host="ftp.example.com", username="u", password="p")
    backend = FtpBackend(profile, ftp_factory=lambda: ftp)
    backend.connect()

    items = backend.list_dir("/remote")

    assert [item.name for item in items] == ["dir", "a.txt"]
    assert items[0].is_dir is True
    assert items[1].size == 3

    local = tmp_path / "upload.txt"
    local.write_bytes(b"hello")
    progress = []
    backend.upload_file(str(local), "/remote/upload.txt", lambda done, total: progress.append((done, total)))
    assert progress[-1] == (5, 5)

    target = tmp_path / "download.txt"
    backend.download_file("/remote/a.txt", str(target))
    assert target.read_bytes() == b"abc"

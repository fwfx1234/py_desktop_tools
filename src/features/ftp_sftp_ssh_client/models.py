from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Literal


ProtocolName = Literal["sftp", "ftp", "ftps"]
AuthKind = Literal["password", "private_key", "agent"]
ConnectionStatus = Literal["disconnected", "connecting", "connected", "error"]
TransferDirection = Literal["upload", "download"]
TransferStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


@dataclass(slots=True)
class RemoteProfile:
    id: str = ""
    name: str = ""
    protocol: ProtocolName = "sftp"
    host: str = ""
    port: int = 22
    username: str = ""
    password: str = ""
    remote_root: str = "/"
    local_root: str = ""
    encoding: str = "utf-8"
    passive_mode: bool = True
    auth_kind: AuthKind = "password"
    private_key_path: str = ""
    private_key_passphrase: str = ""
    connect_timeout: int = 15
    jump_enabled: bool = False
    jump_host: str = ""
    jump_port: int = 22
    jump_username: str = ""
    jump_password: str = ""
    jump_private_key_path: str = ""
    jump_private_key_passphrase: str = ""
    created_at: int = 0
    updated_at: int = 0
    last_used_at: int = 0

    def display_name(self) -> str:
        if self.name.strip():
            return self.name.strip()
        if self.host.strip():
            return f"{self.username}@{self.host}" if self.username else self.host
        return "未命名连接"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.display_name(),
            "rawName": self.name,
            "protocol": self.protocol,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "remoteRoot": self.remote_root,
            "localRoot": self.local_root,
            "encoding": self.encoding,
            "passiveMode": self.passive_mode,
            "authKind": self.auth_kind,
            "privateKeyPath": self.private_key_path,
            "privateKeyPassphrase": self.private_key_passphrase,
            "connectTimeout": self.connect_timeout,
            "jumpEnabled": self.jump_enabled,
            "jumpHost": self.jump_host,
            "jumpPort": self.jump_port,
            "jumpUsername": self.jump_username,
            "jumpPassword": self.jump_password,
            "jumpPrivateKeyPath": self.jump_private_key_path,
            "jumpPrivateKeyPassphrase": self.jump_private_key_passphrase,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "lastUsedAt": self.last_used_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RemoteProfile:
        protocol = _protocol(str(data.get("protocol") or "sftp"))
        default_port = 22 if protocol == "sftp" else 21
        return cls(
            id=str(data.get("id") or ""),
            name=str(data.get("name") or data.get("rawName") or ""),
            protocol=protocol,
            host=str(data.get("host") or ""),
            port=_int(data.get("port"), default_port),
            username=str(data.get("username") or ""),
            password=str(data.get("password") or ""),
            remote_root=_remote_path(str(data.get("remoteRoot") or data.get("remote_root") or "/")),
            local_root=str(data.get("localRoot") or data.get("local_root") or ""),
            encoding=str(data.get("encoding") or "utf-8"),
            passive_mode=bool(data.get("passiveMode", data.get("passive_mode", True))),
            auth_kind=_auth_kind(str(data.get("authKind") or data.get("auth_kind") or "password")),
            private_key_path=str(data.get("privateKeyPath") or data.get("private_key_path") or ""),
            private_key_passphrase=str(data.get("privateKeyPassphrase") or data.get("private_key_passphrase") or ""),
            connect_timeout=max(1, _int(data.get("connectTimeout") or data.get("connect_timeout"), 15)),
            jump_enabled=bool(data.get("jumpEnabled", data.get("jump_enabled", False))),
            jump_host=str(data.get("jumpHost") or data.get("jump_host") or ""),
            jump_port=max(1, _int(data.get("jumpPort") or data.get("jump_port"), 22)),
            jump_username=str(data.get("jumpUsername") or data.get("jump_username") or ""),
            jump_password=str(data.get("jumpPassword") or data.get("jump_password") or ""),
            jump_private_key_path=str(data.get("jumpPrivateKeyPath") or data.get("jump_private_key_path") or ""),
            jump_private_key_passphrase=str(data.get("jumpPrivateKeyPassphrase") or data.get("jump_private_key_passphrase") or ""),
            created_at=_int(data.get("createdAt") or data.get("created_at"), 0),
            updated_at=_int(data.get("updatedAt") or data.get("updated_at"), 0),
            last_used_at=_int(data.get("lastUsedAt") or data.get("last_used_at"), 0),
        )


@dataclass(slots=True)
class RemoteFileItem:
    name: str
    path: str
    is_dir: bool = False
    size: int = 0
    modified_at: int = 0
    permissions: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "isDir": self.is_dir,
            "size": self.size,
            "modifiedAt": self.modified_at,
            "permissions": self.permissions,
        }


@dataclass(slots=True)
class TransferItem:
    id: str
    direction: TransferDirection
    local_path: str
    remote_path: str
    size: int = 0
    transferred: int = 0
    status: TransferStatus = "queued"
    speed: str = "0 KB/s"
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        progress = int((self.transferred * 100) / self.size) if self.size > 0 else 0
        if self.status == "completed":
            progress = 100
        return {
            "id": self.id,
            "direction": self.direction,
            "localPath": self.local_path,
            "remotePath": self.remote_path,
            "name": self.local_path.rsplit("/", 1)[-1] or self.remote_path.rsplit("/", 1)[-1],
            "size": self.size,
            "transferred": self.transferred,
            "progress": progress,
            "status": self.status,
            "speed": self.speed,
            "message": self.message,
        }


@dataclass(slots=True)
class ConnectionSnapshot:
    status: ConnectionStatus = "disconnected"
    profile_id: str = ""
    protocol: str = ""
    host: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "profileId": self.profile_id,
            "protocol": self.protocol,
            "host": self.host,
            "message": self.message,
        }


@dataclass(slots=True)
class RemoteOperationResult:
    local_items: list[dict[str, Any]] | None = None
    remote_items: list[dict[str, Any]] | None = None
    local_path: str = ""
    remote_path: str = ""
    message: str = ""


@dataclass(slots=True)
class TransferCallbacks:
    progress: Any = None
    completed: Any = None
    failed: Any = None


def join_remote_path(base: str, name: str) -> str:
    clean_name = str(name or "").strip("/")
    if not clean_name:
        return _remote_path(base)
    if not base or base == "/":
        return f"/{clean_name}"
    return f"{base.rstrip('/')}/{clean_name}"


def parent_remote_path(path: str) -> str:
    clean = _remote_path(path)
    if clean == "/":
        return "/"
    parent = str(PurePosixPath(clean).parent)
    return parent if parent.startswith("/") else f"/{parent}"


def normalize_profile_payload(data: dict[str, Any]) -> RemoteProfile:
    profile = RemoteProfile.from_dict(data)
    if profile.protocol in {"ftp", "ftps"} and profile.port == 22:
        profile.port = 21
    if profile.protocol == "sftp" and profile.port == 21:
        profile.port = 22
    if not profile.local_root:
        from pathlib import Path

        profile.local_root = str(Path.home())
    return profile


def _protocol(value: str) -> ProtocolName:
    lowered = value.lower()
    if lowered in {"ftp", "ftps", "sftp"}:
        return lowered  # type: ignore[return-value]
    return "sftp"


def _auth_kind(value: str) -> AuthKind:
    lowered = value.lower()
    if lowered in {"password", "private_key", "agent"}:
        return lowered  # type: ignore[return-value]
    return "password"


def _int(value: object, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _remote_path(value: str) -> str:
    text = str(value or "/").strip() or "/"
    if not text.startswith("/"):
        text = "/" + text
    return str(PurePosixPath(text))

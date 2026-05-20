from __future__ import annotations

from pathlib import Path

from app.storage import StorageManager
from features.remote_files.models import RemoteFileItem
from features.remote_files.service import RemoteFilesService


class FakePool:
    def __init__(self, backend) -> None:
        self.backend = backend
        self.profile = None
        self.connected_profiles = []
        self.closed = False

    def connect(self, profile):
        self.profile = profile
        self.connected_profiles.append(profile)
        return self.backend

    def require_backend(self):
        return self.backend

    def close(self) -> None:
        self.closed = True


class ListingBackend:
    def __init__(self, *, fail_list: bool = False) -> None:
        self.fail_list = fail_list
        self.listed_paths = []

    def list_dir(self, path: str):
        self.listed_paths.append(path)
        if self.fail_list:
            raise RuntimeError("permission denied")
        return [RemoteFileItem("a.txt", f"{path.rstrip('/')}/a.txt", False, 3, 0, "")]


def test_connect_keeps_connected_when_initial_remote_listing_fails(tmp_path: Path) -> None:
    database = StorageManager(tmp_path).database("remote_files.db")
    service = RemoteFilesService(database, on_transfers_updated=lambda items: None, on_message=lambda message: None)
    profile = service.profiles.save_profile(
        {
            "name": "prod",
            "protocol": "sftp",
            "host": "example.com",
            "username": "alice",
            "password": "secret",
            "remoteRoot": "/not-readable",
            "localRoot": str(tmp_path),
        }
    )
    backend = ListingBackend(fail_list=True)
    service.pool = FakePool(backend)

    result = service.connect(profile.id)

    assert service.connection_state()["status"] == "connected"
    assert "远程目录读取失败" in service.connection_state()["message"]
    assert result.remote_items == []
    assert result.remote_path == "/not-readable"
    assert result.local_items is not None
    assert backend.listed_paths == ["/not-readable"]

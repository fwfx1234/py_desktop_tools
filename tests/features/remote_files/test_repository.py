from __future__ import annotations

from app.storage import StorageManager
from features.remote_files.repository import RemoteProfileRepository


def test_profile_repository_persists_plaintext_credentials(tmp_path) -> None:
    repo = RemoteProfileRepository(StorageManager(tmp_path).database("remote_files.db"))

    profile = repo.save_profile(
        {
            "name": "Prod",
            "protocol": "sftp",
            "host": "example.com",
            "port": 22,
            "username": "alice",
            "password": "plain-password",
            "remoteRoot": "/srv",
            "localRoot": str(tmp_path),
            "authKind": "private_key",
            "privateKeyPath": "/Users/alice/.ssh/id_ed25519",
            "privateKeyPassphrase": "plain-passphrase",
            "jumpEnabled": True,
            "jumpHost": "jump.example.com",
            "jumpPassword": "jump-plain-password",
        }
    )

    loaded = repo.get_profile(profile.id)

    assert loaded is not None
    assert loaded.password == "plain-password"
    assert loaded.private_key_passphrase == "plain-passphrase"
    assert loaded.jump_password == "jump-plain-password"
    assert loaded.jump_enabled is True
    assert loaded.remote_root == "/srv"


def test_profile_repository_updates_and_deletes(tmp_path) -> None:
    repo = RemoteProfileRepository(StorageManager(tmp_path).database("remote_files.db"))
    created = repo.save_profile({"name": "Old", "protocol": "ftp", "host": "ftp.example.com"})

    repo.save_profile({**created.to_dict(), "name": "New", "protocol": "ftps", "port": 2121})
    profiles = repo.list_profiles()

    assert len(profiles) == 1
    assert profiles[0].name == "New"
    assert profiles[0].protocol == "ftps"
    assert profiles[0].port == 2121

    repo.delete_profile(created.id)

    assert repo.list_profiles() == []

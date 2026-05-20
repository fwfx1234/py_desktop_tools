from __future__ import annotations

import time
from uuid import uuid4

from app.storage import SQLiteDatabase

from .models import RemoteProfile, normalize_profile_payload


class RemoteProfileRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database
        self._ensure_schema()

    def list_profiles(self) -> list[RemoteProfile]:
        with self._database.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, name, protocol, host, port, username, password, remote_root,
                       local_root, encoding, passive_mode, auth_kind, private_key_path,
                       private_key_passphrase, connect_timeout, jump_enabled, jump_host,
                       jump_port, jump_username, jump_password, jump_private_key_path,
                       jump_private_key_passphrase, created_at, updated_at, last_used_at
                FROM remote_file_profiles
                ORDER BY last_used_at DESC, updated_at DESC, created_at DESC
                """
            ).fetchall()
        return [self._profile_from_row(row) for row in rows]

    def get_profile(self, profile_id: str) -> RemoteProfile | None:
        if not profile_id:
            return None
        with self._database.connection() as conn:
            row = conn.execute(
                """
                SELECT id, name, protocol, host, port, username, password, remote_root,
                       local_root, encoding, passive_mode, auth_kind, private_key_path,
                       private_key_passphrase, connect_timeout, jump_enabled, jump_host,
                       jump_port, jump_username, jump_password, jump_private_key_path,
                       jump_private_key_passphrase, created_at, updated_at, last_used_at
                FROM remote_file_profiles
                WHERE id = ?
                """,
                (profile_id,),
            ).fetchone()
        return self._profile_from_row(row) if row is not None else None

    def save_profile(self, payload: dict) -> RemoteProfile:
        profile = normalize_profile_payload(payload)
        now = int(time.time() * 1000)
        if not profile.id:
            profile.id = uuid4().hex
            profile.created_at = now
        if not profile.created_at:
            profile.created_at = now
        profile.updated_at = now
        with self._database.connection() as conn:
            conn.execute(
                """
                INSERT INTO remote_file_profiles (
                    id, name, protocol, host, port, username, password, remote_root,
                    local_root, encoding, passive_mode, auth_kind, private_key_path,
                    private_key_passphrase, connect_timeout, jump_enabled, jump_host,
                    jump_port, jump_username, jump_password, jump_private_key_path,
                    jump_private_key_passphrase, created_at, updated_at, last_used_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    protocol = excluded.protocol,
                    host = excluded.host,
                    port = excluded.port,
                    username = excluded.username,
                    password = excluded.password,
                    remote_root = excluded.remote_root,
                    local_root = excluded.local_root,
                    encoding = excluded.encoding,
                    passive_mode = excluded.passive_mode,
                    auth_kind = excluded.auth_kind,
                    private_key_path = excluded.private_key_path,
                    private_key_passphrase = excluded.private_key_passphrase,
                    connect_timeout = excluded.connect_timeout,
                    jump_enabled = excluded.jump_enabled,
                    jump_host = excluded.jump_host,
                    jump_port = excluded.jump_port,
                    jump_username = excluded.jump_username,
                    jump_password = excluded.jump_password,
                    jump_private_key_path = excluded.jump_private_key_path,
                    jump_private_key_passphrase = excluded.jump_private_key_passphrase,
                    updated_at = excluded.updated_at
                """,
                self._profile_values(profile),
            )
        return profile

    def delete_profile(self, profile_id: str) -> None:
        if not profile_id:
            return
        with self._database.connection() as conn:
            conn.execute("DELETE FROM remote_file_profiles WHERE id = ?", (profile_id,))

    def mark_used(self, profile_id: str) -> None:
        if not profile_id:
            return
        now = int(time.time() * 1000)
        with self._database.connection() as conn:
            conn.execute(
                "UPDATE remote_file_profiles SET last_used_at = ?, updated_at = ? WHERE id = ?",
                (now, now, profile_id),
            )

    def _ensure_schema(self) -> None:
        with self._database.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS remote_file_profiles (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL DEFAULT '',
                    protocol TEXT NOT NULL DEFAULT 'sftp',
                    host TEXT NOT NULL DEFAULT '',
                    port INTEGER NOT NULL DEFAULT 22,
                    username TEXT NOT NULL DEFAULT '',
                    password TEXT NOT NULL DEFAULT '',
                    remote_root TEXT NOT NULL DEFAULT '/',
                    local_root TEXT NOT NULL DEFAULT '',
                    encoding TEXT NOT NULL DEFAULT 'utf-8',
                    passive_mode INTEGER NOT NULL DEFAULT 1,
                    auth_kind TEXT NOT NULL DEFAULT 'password',
                    private_key_path TEXT NOT NULL DEFAULT '',
                    private_key_passphrase TEXT NOT NULL DEFAULT '',
                    connect_timeout INTEGER NOT NULL DEFAULT 15,
                    jump_enabled INTEGER NOT NULL DEFAULT 0,
                    jump_host TEXT NOT NULL DEFAULT '',
                    jump_port INTEGER NOT NULL DEFAULT 22,
                    jump_username TEXT NOT NULL DEFAULT '',
                    jump_password TEXT NOT NULL DEFAULT '',
                    jump_private_key_path TEXT NOT NULL DEFAULT '',
                    jump_private_key_passphrase TEXT NOT NULL DEFAULT '',
                    created_at INTEGER NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL DEFAULT 0,
                    last_used_at INTEGER NOT NULL DEFAULT 0
                )
                """
            )

    @staticmethod
    def _profile_values(profile: RemoteProfile) -> tuple:
        return (
            profile.id,
            profile.name,
            profile.protocol,
            profile.host,
            profile.port,
            profile.username,
            profile.password,
            profile.remote_root,
            profile.local_root,
            profile.encoding,
            1 if profile.passive_mode else 0,
            profile.auth_kind,
            profile.private_key_path,
            profile.private_key_passphrase,
            profile.connect_timeout,
            1 if profile.jump_enabled else 0,
            profile.jump_host,
            profile.jump_port,
            profile.jump_username,
            profile.jump_password,
            profile.jump_private_key_path,
            profile.jump_private_key_passphrase,
            profile.created_at,
            profile.updated_at,
            profile.last_used_at,
        )

    @staticmethod
    def _profile_from_row(row) -> RemoteProfile:
        keys = [
            "id",
            "name",
            "protocol",
            "host",
            "port",
            "username",
            "password",
            "remote_root",
            "local_root",
            "encoding",
            "passive_mode",
            "auth_kind",
            "private_key_path",
            "private_key_passphrase",
            "connect_timeout",
            "jump_enabled",
            "jump_host",
            "jump_port",
            "jump_username",
            "jump_password",
            "jump_private_key_path",
            "jump_private_key_passphrase",
            "created_at",
            "updated_at",
            "last_used_at",
        ]
        data = dict(zip(keys, row, strict=True))
        data["passive_mode"] = bool(data["passive_mode"])
        data["jump_enabled"] = bool(data["jump_enabled"])
        return RemoteProfile.from_dict(data)

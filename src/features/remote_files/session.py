from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Callable

from .backends import RemoteBackend
from .models import ConnectionSnapshot, RemoteProfile
from .terminal_session import RemoteTerminalBridge
from .transfer_service import RemoteTransferService


FTP_LOG_LIMIT = 500


class RemoteSession:
    """All state belonging to one open connection (one profile).

    Held in a registry keyed by ``profile.id``. The user can have several
    sessions alive at once; the UI shows whichever is currently active.
    Each session has its own backend, terminal bridge, transfer queue,
    remote-path cache, and (for FTP) protocol-log buffer.
    """

    def __init__(
        self,
        profile: RemoteProfile,
        backend: RemoteBackend,
        *,
        on_transfers_updated: Callable[[str, list[dict]], None],
        on_message: Callable[[str, str], None],
        on_ftp_log: Callable[[str, str], None] | None = None,
        on_snapshot_changed: Callable[[str], None] | None = None,
    ) -> None:
        self.profile = profile
        self.backend = backend
        self._snapshot = ConnectionSnapshot(
            status="connecting",
            profile_id=profile.id,
            protocol=profile.protocol,
            host=profile.host,
            message="连接中",
        )
        self._snapshot_lock = Lock()
        self._on_snapshot_changed = on_snapshot_changed

        self.local_path: str = ""
        self.remote_path: str = ""
        self.local_items: list[dict] = []
        self.remote_items: list[dict] = []

        self._terminal_bridge: RemoteTerminalBridge | None = None
        self._ftp_log: deque[str] = deque(maxlen=FTP_LOG_LIMIT)
        self._ftp_log_lock = Lock()
        self._on_ftp_log = on_ftp_log

        self.transfers = RemoteTransferService(
            lambda: backend,
            on_transfers_updated=lambda items: on_transfers_updated(profile.id, items),
            on_message=lambda msg: on_message(profile.id, msg),
        )

    @property
    def profile_id(self) -> str:
        return self.profile.id

    @property
    def protocol(self) -> str:
        return self.profile.protocol

    @property
    def terminal_bridge(self) -> RemoteTerminalBridge:
        if self._terminal_bridge is None:
            self._terminal_bridge = RemoteTerminalBridge()
        return self._terminal_bridge

    def has_terminal_bridge(self) -> bool:
        return self._terminal_bridge is not None

    def snapshot(self) -> dict:
        with self._snapshot_lock:
            return self._snapshot.to_dict()

    def set_snapshot(self, snapshot: ConnectionSnapshot) -> None:
        with self._snapshot_lock:
            self._snapshot = snapshot
        if self._on_snapshot_changed is not None:
            self._on_snapshot_changed(self.profile.id)

    def update_snapshot(self, **changes) -> None:
        with self._snapshot_lock:
            current = self._snapshot
            self._snapshot = ConnectionSnapshot(
                status=changes.get("status", current.status),
                profile_id=changes.get("profile_id", current.profile_id),
                protocol=changes.get("protocol", current.protocol),
                host=changes.get("host", current.host),
                message=changes.get("message", current.message),
            )
        if self._on_snapshot_changed is not None:
            self._on_snapshot_changed(self.profile.id)

    def append_ftp_log(self, line: str) -> None:
        if not line:
            return
        with self._ftp_log_lock:
            self._ftp_log.append(line)
        if self._on_ftp_log is not None:
            self._on_ftp_log(self.profile.id, line)

    def ftp_log_snapshot(self) -> list[str]:
        with self._ftp_log_lock:
            return list(self._ftp_log)

    def clear_ftp_log(self) -> None:
        with self._ftp_log_lock:
            self._ftp_log.clear()
        if self._on_ftp_log is not None:
            self._on_ftp_log(self.profile.id, "")

    def close(self) -> None:
        try:
            if self._terminal_bridge is not None:
                self._terminal_bridge.close()
        finally:
            self._terminal_bridge = None
        try:
            self.transfers.close()
        except Exception:
            pass
        try:
            self.backend.close()
        except Exception:
            pass

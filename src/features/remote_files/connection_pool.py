from __future__ import annotations

from threading import Lock

from .session import RemoteSession


class RemoteConnectionPool:
    """Registry of live remote sessions, keyed by profile id.

    Replaces the previous single-slot pool. Opening a new session never
    closes an existing one; callers must explicitly close per profile id.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, RemoteSession] = {}
        self._lock = Lock()

    def add(self, session: RemoteSession) -> None:
        with self._lock:
            existing = self._sessions.get(session.profile_id)
            self._sessions[session.profile_id] = session
        if existing is not None and existing is not session:
            try:
                existing.close()
            except Exception:
                pass

    def get(self, profile_id: str) -> RemoteSession | None:
        with self._lock:
            return self._sessions.get(profile_id)

    def require(self, profile_id: str) -> RemoteSession:
        session = self.get(profile_id)
        if session is None:
            raise RuntimeError("会话不存在或未连接")
        return session

    def has(self, profile_id: str) -> bool:
        with self._lock:
            return profile_id in self._sessions

    def list_sessions(self) -> list[RemoteSession]:
        with self._lock:
            return list(self._sessions.values())

    def remove(self, profile_id: str) -> RemoteSession | None:
        with self._lock:
            return self._sessions.pop(profile_id, None)

    def close_session(self, profile_id: str) -> None:
        session = self.remove(profile_id)
        if session is not None:
            try:
                session.close()
            except Exception:
                pass

    def close_all(self) -> None:
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            try:
                session.close()
            except Exception:
                pass

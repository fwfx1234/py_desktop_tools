from __future__ import annotations

from threading import Lock

from .backends import RemoteBackend, create_backend
from .models import RemoteProfile


class RemoteConnectionPool:
    def __init__(self) -> None:
        self._backend: RemoteBackend | None = None
        self._profile: RemoteProfile | None = None
        self._lock = Lock()

    @property
    def profile(self) -> RemoteProfile | None:
        with self._lock:
            return self._profile

    @property
    def backend(self) -> RemoteBackend | None:
        with self._lock:
            return self._backend

    def connect(self, profile: RemoteProfile) -> RemoteBackend:
        backend = create_backend(profile)
        backend.connect()
        with self._lock:
            old = self._backend
            self._backend = backend
            self._profile = profile
        if old is not None:
            old.close()
        return backend

    def require_backend(self) -> RemoteBackend:
        with self._lock:
            backend = self._backend
        if backend is None:
            raise RuntimeError("尚未连接远程服务器")
        return backend

    def close(self) -> None:
        with self._lock:
            backend = self._backend
            self._backend = None
            self._profile = None
        if backend is not None:
            backend.close()

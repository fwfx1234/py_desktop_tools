from __future__ import annotations

import time
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.concurrency import PythonTaskRunner, TaskHandle
from app.logging import get_logger

from .backends import RemoteBackend
from .models import TransferDirection, TransferItem

_LOG = None


def _logger():
    global _LOG
    if _LOG is None:
        _LOG = get_logger("features.remote_files.transfer_service", plugin_id="remote-files")
    return _LOG


class TransferCancelled(RuntimeError):
    pass


class RemoteTransferService:
    def __init__(
        self,
        backend_getter,
        *,
        on_transfers_updated,
        on_message,
    ) -> None:
        self._backend_getter = backend_getter
        self._on_transfers_updated = on_transfers_updated
        self._on_message = on_message
        self._runner = PythonTaskRunner(max_workers=3, thread_name_prefix="remote-transfer")
        self._items: dict[str, TransferItem] = {}
        self._handles: dict[str, TaskHandle] = {}
        self._lock = Lock()

    def start_upload(self, local_path: str, remote_path: str) -> str:
        size = _local_size(local_path)
        return self._start("upload", local_path, remote_path, size)

    def start_download(self, remote_path: str, local_path: str, size: int = 0) -> str:
        return self._start("download", local_path, remote_path, size)

    def cancel(self, transfer_id: str) -> None:
        _logger().info("remote_files.transfer.cancel", "取消传输", transferId=transfer_id)
        with self._lock:
            handle = self._handles.get(transfer_id)
            item = self._items.get(transfer_id)
            if item is not None and item.status in {"queued", "running"}:
                item.status = "cancelled"
                item.message = "已取消"
        if handle is not None:
            handle.cancel()
        self._emit()

    def items(self) -> list[dict]:
        with self._lock:
            values = [item.to_dict() for item in self._items.values()]
        return values

    def clear_finished(self) -> None:
        _logger().info("remote_files.transfer.clear_finished", "清理已完成传输")
        with self._lock:
            self._items = {
                item_id: item
                for item_id, item in self._items.items()
                if item.status in {"queued", "running"}
            }
        self._emit()

    def close(self) -> None:
        _logger().info("remote_files.transfer.close", "关闭传输服务")
        self._runner.shutdown(wait=False)

    def _start(self, direction: TransferDirection, local_path: str, remote_path: str, size: int) -> str:
        transfer_id = uuid4().hex
        _logger().info(
            "remote_files.transfer.queued",
            "传输任务已加入队列",
            transferId=transfer_id,
            direction=direction,
            localPath=local_path,
            remotePath=remote_path,
            size=size,
        )
        item = TransferItem(
            id=transfer_id,
            direction=direction,
            local_path=local_path,
            remote_path=remote_path,
            size=size,
        )
        with self._lock:
            self._items[transfer_id] = item
        self._emit()
        handle = self._runner.start(
            lambda task_handle: self._run_transfer(task_handle, transfer_id),
            on_error=lambda exc: self._mark_failed(transfer_id, exc),
            on_done=lambda: self._remove_handle(transfer_id),
        )
        with self._lock:
            self._handles[transfer_id] = handle
        return transfer_id

    def _run_transfer(self, handle: TaskHandle, transfer_id: str) -> None:
        backend: RemoteBackend = self._backend_getter()
        with self._lock:
            item = self._items[transfer_id]
            item.status = "running"
            item.message = "传输中"
        _logger().info(
            "remote_files.transfer.running",
            "传输任务开始",
            transferId=transfer_id,
            direction=item.direction,
            localPath=item.local_path,
            remotePath=item.remote_path,
            size=item.size,
        )
        self._emit()
        started_at = time.time()

        def progress(done: int, total: int) -> None:
            if handle.cancelled:
                raise TransferCancelled("传输已取消")
            elapsed = max(time.time() - started_at, 0.1)
            with self._lock:
                current = self._items.get(transfer_id)
                if current is None:
                    return
                current.transferred = int(done)
                if total:
                    current.size = int(total)
                current.speed = f"{done / 1024 / elapsed:.1f} KB/s"
            self._emit()

        try:
            if item.direction == "upload":
                backend.upload_file(item.local_path, item.remote_path, progress)
            else:
                backend.download_file(item.remote_path, item.local_path, progress)
        except TransferCancelled:
            with self._lock:
                item = self._items.get(transfer_id)
                if item is not None:
                    item.status = "cancelled"
                    item.message = "已取消"
            _logger().info("remote_files.transfer.cancelled", "传输任务已取消", transferId=transfer_id)
            self._emit()
            return

        with self._lock:
            item = self._items.get(transfer_id)
            if item is not None:
                item.status = "completed"
                item.transferred = item.size if item.size else item.transferred
                item.speed = "0 KB/s"
                item.message = "已完成"
        _logger().info("remote_files.transfer.completed", "传输任务已完成", transferId=transfer_id)
        self._emit()
        self._on_message("传输完成")

    def _mark_failed(self, transfer_id: str, exc: BaseException) -> None:
        _logger().error("remote_files.transfer.failed", "传输任务失败", transferId=transfer_id, error=str(exc))
        with self._lock:
            item = self._items.get(transfer_id)
            if item is not None and item.status != "cancelled":
                item.status = "failed"
                item.message = str(exc)
                item.speed = "0 KB/s"
        self._emit()
        self._on_message(f"传输失败: {exc}")

    def _remove_handle(self, transfer_id: str) -> None:
        with self._lock:
            self._handles.pop(transfer_id, None)

    def _emit(self) -> None:
        self._on_transfers_updated(self.items())


def _local_size(path: str) -> int:
    try:
        return Path(path).stat().st_size
    except OSError:
        return 0

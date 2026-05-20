from __future__ import annotations

import re
import time
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Callable
from urllib.parse import unquote, urlparse

import requests

from app.concurrency import PythonTaskRunner, TaskHandle
from app.logging import get_logger, make_task_id


DEFAULT_SAVE_ROOT = Path.home() / "Downloads" / "PyDesktopTools" / "Downloads"


class DownloadService:
    def __init__(
        self,
        on_tasks_updated: Callable[[list[dict]], None],
        on_download_finished: Callable[[str], None],
        save_root: Path | None = None,
    ) -> None:
        self._on_tasks_updated = on_tasks_updated
        self._on_download_finished = on_download_finished
        self._tasks: list[dict] = []
        self._cancelled: set[str] = set()
        self._lock = Lock()
        self._runner = PythonTaskRunner(thread_name_prefix="download-task")
        self._task_handles: dict[str, TaskHandle] = {}
        self._log = get_logger("features.download.service", plugin_id="download")
        self._save_root = save_root or DEFAULT_SAVE_ROOT

    @property
    def save_root(self) -> Path:
        return self._save_root

    def download_file(self, url: str, save_path: str) -> str:
        target = Path(save_path)
        return self._start_task(url, target)

    def download_url(self, url: str) -> str:
        try:
            self._save_root.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self._on_download_finished(f"无法创建下载目录: {exc}")
            return ""
        target = self._unique_path(self._save_root / _filename_from_url(url))
        return self._start_task(url, target)

    def clear_tasks(self) -> None:
        with self._lock:
            self._tasks = []
        self._emit_tasks()

    def clear_completed(self) -> None:
        with self._lock:
            self._tasks = [t for t in self._tasks if t.get("status") != "下载完成"]
        self._emit_tasks()

    def clear_failed(self) -> None:
        with self._lock:
            self._tasks = [t for t in self._tasks if not str(t.get("status", "")).startswith("失败")]
        self._emit_tasks()

    def remove_task(self, task_id: str) -> None:
        clean = str(task_id or "")
        if not clean:
            return
        with self._lock:
            self._tasks = [t for t in self._tasks if t.get("id") != clean]
            self._cancelled.add(clean)
            handle = self._task_handles.pop(clean, None)
        if handle is not None:
            handle.cancel()
        self._emit_tasks()

    def cancel_task(self, task_id: str) -> None:
        clean_id = str(task_id or "")
        if not clean_id:
            return
        with self._lock:
            self._cancelled.add(clean_id)
            handle = self._task_handles.get(clean_id)
        if handle is not None:
            handle.cancel()
        self._log.info("download.cancel_requested", "请求取消下载", taskId=clean_id)
        self._update_task(clean_id, {"status": "正在取消", "speed": "0 KB/s"})

    def retry_task(self, task_id: str) -> str:
        snapshot = self._snapshot_task(task_id)
        if snapshot is None:
            return ""
        url = str(snapshot.get("url", ""))
        save_path = str(snapshot.get("savePath") or "")
        if not url:
            return ""
        with self._lock:
            self._tasks = [t for t in self._tasks if t.get("id") != task_id]
        if save_path:
            target = Path(save_path)
        else:
            try:
                self._save_root.mkdir(parents=True, exist_ok=True)
            except Exception:
                return ""
            target = self._unique_path(self._save_root / _filename_from_url(url))
        return self._start_task(url, target)

    def close(self) -> None:
        with self._lock:
            self._cancelled.update(str(task.get("id") or "") for task in self._tasks)
            self._task_handles.clear()
        self._runner.shutdown(wait=False)

    def get_task(self, task_id: str) -> dict | None:
        return self._snapshot_task(task_id)

    def _start_task(self, url: str, target: Path) -> str:
        task_id = make_task_id()
        domain = _domain_from_url(url)
        task = {
            "id": task_id,
            "url": url,
            "domain": domain,
            "savePath": str(target),
            "fileName": target.name,
            "status": "排队中",
            "progress": 0,
            "speed": "0 KB/s",
            "writtenBytes": 0,
            "totalBytes": 0,
            "elapsedMs": 0,
            "error": "",
            "startedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        with self._lock:
            self._tasks.append(task)
        self._log.info(
            "download.start",
            "开始下载",
            taskId=task_id,
            urlLength=len(url or ""),
            targetName=target.name,
        )
        self._emit_tasks()
        handle = self._runner.start(
            lambda task_handle: self._download_worker(task_handle, task_id, url, target),
            on_success=lambda message: self._on_download_finished(str(message or "")),
            on_error=lambda exc: self._handle_download_error(task_id, exc),
            on_done=lambda: self._remove_task_handle(task_id),
        )
        should_cancel = False
        with self._lock:
            if task_id in self._cancelled:
                should_cancel = True
            elif handle._future is None or not handle._future.done():
                self._task_handles[task_id] = handle
        if should_cancel:
            handle.cancel()
        return task_id

    def _download_worker(self, handle: TaskHandle, task_id: str, url: str, target: Path) -> str:
        target.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        total = 0
        start_at = time.time()
        try:
            with requests.get(url, stream=True, timeout=30) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", "0") or "0")
                disposition = resp.headers.get("content-disposition", "")
                inferred = _filename_from_disposition(disposition)
                if inferred and target.name.startswith("download_"):
                    new_target = self._unique_path(target.parent / inferred)
                    target = new_target
                self._update_task(task_id, {
                    "status": "下载中",
                    "totalBytes": total,
                    "fileName": target.name,
                    "savePath": str(target),
                })
                with target.open("wb") as file_obj:
                    for chunk in resp.iter_content(chunk_size=1024 * 64):
                        if self._is_cancelled(task_id) or handle.cancelled:
                            self._remove_partial(target)
                            self._update_task(task_id, {
                                "status": "已取消",
                                "progress": 0,
                                "speed": "0 KB/s",
                                "elapsedMs": int((time.time() - start_at) * 1000),
                            })
                            self._log.info("download.cancelled", "下载已取消", taskId=task_id, targetName=target.name)
                            return f"已取消: {target.name}"
                        if not chunk:
                            continue
                        file_obj.write(chunk)
                        written += len(chunk)
                        elapsed = max(time.time() - start_at, 0.1)
                        speed_kb = written / 1024 / elapsed
                        progress = int((written * 100) / total) if total > 0 else 0
                        self._update_task(
                            task_id,
                            {
                                "status": "下载中",
                                "progress": progress,
                                "speed": f"{speed_kb:.1f} KB/s",
                                "writtenBytes": written,
                                "elapsedMs": int(elapsed * 1000),
                            },
                        )
        finally:
            with self._lock:
                self._cancelled.discard(task_id)
        elapsed_ms = int((time.time() - start_at) * 1000)
        self._update_task(task_id, {
            "status": "下载完成",
            "progress": 100,
            "speed": "0 KB/s",
            "writtenBytes": written,
            "totalBytes": total if total else written,
            "elapsedMs": elapsed_ms,
        })
        self._log.info("download.complete", "下载完成", taskId=task_id, targetName=target.name, bytes=written)
        return f"下载完成: {target.name}"

    def _handle_download_error(self, task_id: str, exc: BaseException) -> None:
        message = str(exc)
        self._update_task(task_id, {
            "status": f"失败: {message}",
            "speed": "0 KB/s",
            "error": message,
        })
        self._log.warning("download.failed", "下载失败", taskId=task_id, error=message)
        self._on_download_finished(f"下载失败: {message}")

    def _update_task(self, task_id: str, data: dict) -> None:
        with self._lock:
            for task in self._tasks:
                if task.get("id") == task_id:
                    task.update(data)
                    break
        self._emit_tasks()

    def _emit_tasks(self) -> None:
        with self._lock:
            items = [dict(task) for task in self._tasks]
        self._on_tasks_updated(items)

    def _snapshot_task(self, task_id: str) -> dict | None:
        with self._lock:
            for task in self._tasks:
                if task.get("id") == task_id:
                    return dict(task)
        return None

    def _is_cancelled(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self._cancelled

    def _remove_task_handle(self, task_id: str) -> None:
        with self._lock:
            self._task_handles.pop(task_id, None)

    @staticmethod
    def _remove_partial(target: Path) -> None:
        try:
            if target.exists():
                target.unlink()
        except OSError:
            pass

    @staticmethod
    def _unique_path(target: Path) -> Path:
        if not target.exists():
            return target
        stem = target.stem
        suffix = target.suffix
        parent = target.parent
        counter = 1
        while True:
            candidate = parent / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1


def _domain_from_url(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def _filename_from_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        candidate = unquote(Path(parsed.path).name)
        if candidate:
            return _sanitize_filename(candidate)
    except Exception:
        pass
    return f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _filename_from_disposition(value: str) -> str:
    if not value:
        return ""
    match = re.search(r"filename\*=(?:UTF-8'')?([^;]+)", value, flags=re.IGNORECASE)
    if match:
        return _sanitize_filename(unquote(match.group(1).strip().strip('"')))
    match = re.search(r"filename=\"?([^\";]+)\"?", value, flags=re.IGNORECASE)
    if match:
        return _sanitize_filename(match.group(1).strip())
    return ""


def _sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]", "_", name).strip()
    return cleaned or f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

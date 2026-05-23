from __future__ import annotations

import re
import time
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Callable
from urllib.parse import unquote, urlparse

from app.concurrency import PythonTaskRunner, TaskHandle
from app.logging import get_logger, make_task_id

from .repository import DownloadManagerRepository


DEFAULT_SAVE_ROOT = Path.home() / "Downloads" / "PyDesktopTools" / "Downloads"
DEFAULT_MAX_CONCURRENT = 3
DEFAULT_TIMEOUT_SEC = 30
DEFAULT_RETRY_LIMIT = 2
MAX_RETRY_LIMIT = 10
MAX_TIMEOUT_SEC = 3600
CHUNK_SIZE = 1024 * 64


class DownloadManagerService:
    def __init__(
        self,
        on_tasks_updated: Callable[[list[dict]], None],
        on_download_finished: Callable[[str], None],
        repository: DownloadManagerRepository | None = None,
        save_root: Path | None = None,
    ) -> None:
        self._on_tasks_updated = on_tasks_updated
        self._on_download_finished = on_download_finished
        self._repository = repository
        self._tasks: list[dict] = []
        self._paused: set[str] = set()
        self._cancelled: set[str] = set()
        self._lock = Lock()
        self._runner = PythonTaskRunner(thread_name_prefix="download-manager-task")
        self._task_handles: dict[str, TaskHandle] = {}
        self._log = get_logger("features.download_manager.service", plugin_id="download-manager")
        self._save_root = save_root or DEFAULT_SAVE_ROOT
        self._max_concurrent = DEFAULT_MAX_CONCURRENT
        self._speed_limit_kbps = 0
        self._timeout_sec = DEFAULT_TIMEOUT_SEC
        self._retry_limit = DEFAULT_RETRY_LIMIT
        self._proxy_url = ""
        self._user_agent = ""
        self._referer = ""
        self._cookie = ""
        self._custom_headers = ""
        self._load_persisted_state()

    @property
    def save_root(self) -> Path:
        return self._save_root

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    @property
    def speed_limit_kbps(self) -> int:
        return self._speed_limit_kbps

    @property
    def timeout_sec(self) -> int:
        return self._timeout_sec

    @property
    def retry_limit(self) -> int:
        return self._retry_limit

    def settings(self) -> dict:
        return {
            "saveRoot": str(self._save_root),
            "maxConcurrent": self._max_concurrent,
            "speedLimitKbps": self._speed_limit_kbps,
            "timeoutSec": self._timeout_sec,
            "retryLimit": self._retry_limit,
            "proxyUrl": self._proxy_url,
            "userAgent": self._user_agent,
            "referer": self._referer,
            "cookie": self._cookie,
            "customHeaders": self._custom_headers,
        }

    def tasks_snapshot(self) -> list[dict]:
        with self._lock:
            return [dict(task) for task in self._tasks]

    def set_max_concurrent(self, value: int) -> None:
        self._max_concurrent = max(1, min(int(value or 1), 16))
        self._persist_settings()
        self._dispatch_queue()
        self._emit_tasks()

    def set_speed_limit_kbps(self, value: int) -> None:
        self._speed_limit_kbps = max(0, int(value or 0))
        self._persist_settings()
        self._emit_tasks()

    def set_save_root(self, value: str) -> bool:
        target = _path_from_ui(value)
        if target is None:
            return False
        try:
            target.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self._on_download_finished(f"无法创建下载目录: {exc}")
            return False
        self._save_root = target
        self._persist_settings()
        self._emit_tasks()
        return True

    def set_network_options(
        self,
        *,
        user_agent: str,
        referer: str,
        cookie: str,
        custom_headers: str,
        proxy_url: str,
        timeout_sec: int,
        retry_limit: int,
    ) -> None:
        self._user_agent = str(user_agent or "").strip()
        self._referer = str(referer or "").strip()
        self._cookie = str(cookie or "").strip()
        self._custom_headers = str(custom_headers or "").strip()
        self._proxy_url = _normalize_proxy_url(proxy_url)
        self._timeout_sec = _sanitize_timeout_sec(timeout_sec)
        self._retry_limit = _sanitize_retry_limit(retry_limit)
        self._persist_settings()
        self._emit_tasks()

    def download_file(self, url: str, save_path: str) -> str:
        target = Path(save_path)
        task_id = self._create_task(url, target)
        self._dispatch_queue()
        return task_id

    def download_url(self, url: str) -> str:
        duplicate = self._find_existing_url(url)
        if duplicate is not None and duplicate.get("state") in {"queued", "running", "paused", "pausing"}:
            self._on_download_finished(f"任务已存在: {duplicate.get('fileName') or duplicate.get('url')}")
            return ""
        try:
            self._save_root.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self._on_download_finished(f"无法创建下载目录: {exc}")
            return ""
        target = self._unique_path(self._save_root / _filename_from_url(url))
        task_id = self._create_task(url, target)
        self._dispatch_queue()
        return task_id

    def download_urls(self, text: str) -> list[str]:
        task_ids: list[str] = []
        urls = _extract_urls(text)
        for url in urls:
            task_id = self.download_url(url)
            if task_id:
                task_ids.append(task_id)
        return task_ids

    def clear_tasks(self) -> None:
        with self._lock:
            for task in self._tasks:
                task_id = str(task.get("id") or "")
                if task_id:
                    self._cancelled.add(task_id)
                handle = self._task_handles.pop(task_id, None)
                if handle is not None:
                    handle.cancel()
            self._tasks = []
            self._paused.clear()
        if self._repository is not None:
            self._repository.clear_tasks()
        self._emit_tasks()

    def clear_completed(self) -> None:
        with self._lock:
            self._tasks = [t for t in self._tasks if t.get("state") != "completed"]
        if self._repository is not None:
            self._repository.delete_tasks_by_states({"completed"})
        self._emit_tasks()

    def clear_failed(self) -> None:
        with self._lock:
            self._tasks = [t for t in self._tasks if t.get("state") not in {"failed", "cancelled"}]
        if self._repository is not None:
            self._repository.delete_tasks_by_states({"failed", "cancelled"})
        self._emit_tasks()

    def remove_task(self, task_id: str) -> None:
        clean = str(task_id or "")
        if not clean:
            return
        partial_path = ""
        handle = None
        with self._lock:
            for task in self._tasks:
                if task.get("id") == clean:
                    partial_path = str(task.get("partialPath") or "")
                    break
            self._tasks = [t for t in self._tasks if t.get("id") != clean]
            self._cancelled.add(clean)
            self._paused.discard(clean)
            handle = self._task_handles.pop(clean, None)
        if handle is not None:
            handle.cancel()
        _remove_path(partial_path)
        if self._repository is not None:
            self._repository.delete_task(clean)
        if handle is None:
            self._dispatch_queue()
        self._emit_tasks()

    def cancel_task(self, task_id: str) -> None:
        clean_id = str(task_id or "")
        if not clean_id:
            return
        with self._lock:
            self._cancelled.add(clean_id)
            self._paused.discard(clean_id)
            handle = self._task_handles.get(clean_id)
        if handle is not None:
            handle.cancel()
        self._log.info("download.cancel_requested", "请求取消下载", taskId=clean_id)
        self._update_task(
            clean_id,
            {
                "state": "cancelling" if handle is not None else "cancelled",
                "status": "取消中" if handle is not None else "已取消",
                "speed": "0 KB/s",
            },
        )
        if handle is None:
            self._dispatch_queue()

    def pause_task(self, task_id: str) -> None:
        clean_id = str(task_id or "")
        if not clean_id:
            return
        with self._lock:
            self._paused.add(clean_id)
            handle = self._task_handles.get(clean_id)
        if handle is not None:
            handle.cancel()
        self._update_task(
            clean_id,
            {
                "state": "pausing" if handle is not None else "paused",
                "status": "暂停中" if handle is not None else "已暂停",
                "speed": "0 KB/s",
            },
        )
        if handle is None:
            self._dispatch_queue()

    def resume_task(self, task_id: str) -> None:
        clean_id = str(task_id or "")
        if not clean_id:
            return
        with self._lock:
            if clean_id in self._task_handles:
                return
            self._paused.discard(clean_id)
            self._cancelled.discard(clean_id)
            for task in self._tasks:
                if task.get("id") == clean_id and task.get("state") in {"paused", "failed", "cancelled", "cancelling"}:
                    data = {"state": "queued", "status": "排队中", "speed": "0 KB/s", "error": ""}
                    if task.get("state") in {"failed", "cancelled", "cancelling"}:
                        data["attempts"] = 0
                    task.update(data)
                    self._persist_task(task)
                    break
        self._dispatch_queue()
        self._emit_tasks()

    def pause_all(self) -> None:
        with self._lock:
            task_ids = [str(t.get("id") or "") for t in self._tasks if t.get("state") in {"queued", "running"}]
        for task_id in task_ids:
            self.pause_task(task_id)

    def resume_all(self) -> None:
        with self._lock:
            task_ids = [str(t.get("id") or "") for t in self._tasks if t.get("state") in {"paused", "failed", "cancelled", "cancelling"}]
        for task_id in task_ids:
            self.resume_task(task_id)

    def retry_task(self, task_id: str) -> str:
        clean_id = str(task_id or "")
        with self._lock:
            if clean_id in self._task_handles:
                return ""
            self._paused.discard(clean_id)
            self._cancelled.discard(clean_id)
            found = False
            for task in self._tasks:
                if task.get("id") == clean_id:
                    found = True
                    task.update({"state": "queued", "status": "排队中", "speed": "0 KB/s", "error": "", "attempts": 0})
                    self._persist_task(task)
                    break
        if not found:
            return ""
        self._dispatch_queue()
        self._emit_tasks()
        return clean_id

    def close(self) -> None:
        with self._lock:
            self._cancelled.update(str(task.get("id") or "") for task in self._tasks)
            self._task_handles.clear()
        self._runner.shutdown(wait=False)

    def get_task(self, task_id: str) -> dict | None:
        return self._snapshot_task(task_id)

    def _create_task(self, url: str, target: Path) -> str:
        task_id = make_task_id()
        clean_url = str(url or "").strip()
        domain = _domain_from_url(clean_url)
        partial = target.with_name(f"{target.name}.part")
        category = _category_from_filename(target.name)
        task = {
            "id": task_id,
            "url": clean_url,
            "domain": domain,
            "category": category,
            "savePath": str(target),
            "partialPath": str(partial),
            "fileName": target.name,
            "status": "排队中",
            "state": "queued",
            "progress": 0,
            "speed": "0 KB/s",
            "writtenBytes": 0,
            "totalBytes": 0,
            "eta": "-",
            "elapsedMs": 0,
            "error": "",
            "resumable": False,
            "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "startedAt": "",
            "finishedAt": "",
            "attempts": 0,
            **self._network_snapshot(),
        }
        with self._lock:
            self._tasks.append(task)
        self._persist_task(task)
        self._log.info(
            "download.queued",
            "下载任务已加入队列",
            taskId=task_id,
            urlLength=len(clean_url),
            targetName=target.name,
        )
        self._emit_tasks()
        return task_id

    def _load_persisted_state(self) -> None:
        if self._repository is None:
            return
        settings = self._repository.load_settings()
        save_root = settings.get("saveRoot", "").strip()
        if save_root:
            self._save_root = Path(save_root)
        try:
            self._max_concurrent = max(1, min(int(settings.get("maxConcurrent") or DEFAULT_MAX_CONCURRENT), 16))
        except ValueError:
            self._max_concurrent = DEFAULT_MAX_CONCURRENT
        try:
            self._speed_limit_kbps = max(0, int(settings.get("speedLimitKbps") or 0))
        except ValueError:
            self._speed_limit_kbps = 0
        self._timeout_sec = _sanitize_timeout_sec(settings.get("timeoutSec") or DEFAULT_TIMEOUT_SEC)
        self._retry_limit = _sanitize_retry_limit(settings.get("retryLimit") or DEFAULT_RETRY_LIMIT)
        self._proxy_url = _normalize_proxy_url(settings.get("proxyUrl") or "")
        self._user_agent = str(settings.get("userAgent") or "").strip()
        self._referer = str(settings.get("referer") or "").strip()
        self._cookie = str(settings.get("cookie") or "").strip()
        self._custom_headers = str(settings.get("customHeaders") or "").strip()
        restored: list[dict] = []
        for task in self._repository.list_tasks():
            normalized = self._normalize_persisted_task(task)
            if normalized is not None:
                restored.append(normalized)
        self._tasks = restored
        self._paused = {str(task.get("id") or "") for task in restored if task.get("state") == "paused"}

    def _normalize_persisted_task(self, task: dict) -> dict | None:
        task_id = str(task.get("id") or "")
        url = str(task.get("url") or "")
        if not task_id or not url:
            return None
        state = str(task.get("state") or "")
        if state in {"running", "queued", "pausing"}:
            state = "paused"
        if state == "cancelling":
            state = "cancelled"
        task["state"] = state or "paused"
        task["status"] = state_label_for_persisted(task["state"])
        task["speed"] = "0 KB/s"
        task["eta"] = "-"
        if not task.get("category"):
            task["category"] = _category_from_filename(str(task.get("fileName") or ""))
        if not task.get("partialPath") and task.get("savePath"):
            target = Path(str(task.get("savePath") or ""))
            task["partialPath"] = str(target.with_name(f"{target.name}.part"))
        for key, value in self._network_snapshot().items():
            task.setdefault(key, value)
        return task

    def _dispatch_queue(self) -> None:
        while True:
            with self._lock:
                running = sum(1 for task in self._tasks if task.get("state") == "running")
                if running >= self._max_concurrent:
                    return
                next_task = None
                for task in self._tasks:
                    task_id = str(task.get("id") or "")
                    if task.get("state") == "queued" and task_id not in self._paused:
                        task.update(
                            {
                                "state": "running",
                                "status": "下载中",
                                "speed": "0 KB/s",
                                "startedAt": task.get("startedAt") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "attempts": int(task.get("attempts") or 0) + 1,
                            }
                        )
                        next_task = dict(task)
                        self._persist_task(task)
                        break
                if next_task is None:
                    return
            self._emit_tasks()
            self._start_worker(next_task)

    def _start_worker(self, task: dict) -> None:
        task_id = str(task.get("id") or "")
        url = str(task.get("url") or "")
        target = Path(str(task.get("savePath") or ""))
        handle = self._runner.start(
            lambda task_handle: self._download_worker(task_handle, task_id, url, target, task),
            on_success=lambda message: self._on_download_finished(str(message or "")),
            on_error=lambda exc: self._handle_download_error(task_id, exc),
            on_done=lambda: self._worker_done(task_id),
        )
        should_cancel = False
        with self._lock:
            if task_id in self._cancelled or task_id in self._paused:
                should_cancel = True
            elif handle._future is None or not handle._future.done():
                self._task_handles[task_id] = handle
        if should_cancel:
            handle.cancel()

    def _download_worker(self, handle: TaskHandle, task_id: str, url: str, target: Path, task: dict) -> str:
        import requests

        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(f"{target.name}.part")
        existing = partial.stat().st_size if partial.exists() else 0
        start_at = time.time()
        window_start = start_at
        window_bytes = 0
        total_written = existing
        headers = _headers_for_task(task, existing)
        proxies = _proxies_for_task(task)
        timeout = _sanitize_timeout_sec(_task_option(task, "timeoutSec", self._timeout_sec))

        try:
            with requests.get(url, headers=headers, proxies=proxies, stream=True, timeout=timeout) as resp:
                if existing > 0 and resp.status_code == 200:
                    existing = 0
                    total_written = 0
                    self._remove_partial(partial)
                resp.raise_for_status()
                accept_ranges = str(resp.headers.get("accept-ranges", "")).lower() == "bytes"
                total = _total_size_from_response(resp, existing)
                disposition = resp.headers.get("content-disposition", "")
                inferred = _filename_from_disposition(disposition)
                if inferred and target.name.startswith("download_") and existing == 0:
                    new_target = self._unique_path(target.parent / inferred)
                    target = new_target
                    partial = target.with_name(f"{target.name}.part")
                    self._update_task(
                        task_id,
                        {
                            "fileName": target.name,
                            "savePath": str(target),
                            "partialPath": str(partial),
                            "category": _category_from_filename(target.name),
                        },
                    )
                self._update_task(
                    task_id,
                    {
                        "state": "running",
                        "status": "下载中",
                        "totalBytes": total,
                        "writtenBytes": total_written,
                        "resumable": accept_ranges or resp.status_code == 206,
                    },
                )
                with partial.open("ab" if existing > 0 else "wb") as file_obj:
                    for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                        if self._is_cancelled(task_id) or handle.cancelled:
                            state = "paused" if self._is_paused(task_id) else "cancelled"
                            status = "已暂停" if state == "paused" else "已取消"
                            if state == "cancelled":
                                self._remove_partial(partial)
                                total_written = 0
                            self._update_task(
                                task_id,
                                {
                                    "state": state,
                                    "status": status,
                                    "progress": int((total_written * 100) / total) if total > 0 else 0,
                                    "speed": "0 KB/s",
                                    "writtenBytes": total_written,
                                    "elapsedMs": int((time.time() - start_at) * 1000),
                                },
                            )
                            self._log.info("download.stopped", "下载已停止", taskId=task_id, state=state)
                            return f"{status}: {target.name}"
                        if not chunk:
                            continue
                        file_obj.write(chunk)
                        total_written += len(chunk)
                        window_bytes += len(chunk)
                        self._throttle(window_bytes, window_start)
                        elapsed = max(time.time() - start_at, 0.1)
                        speed_kb = max((total_written - existing), 0) / 1024 / elapsed
                        progress = int((total_written * 100) / total) if total > 0 else 0
                        eta = _format_eta((total - total_written) / 1024 / speed_kb) if total > 0 and speed_kb > 0 else "-"
                        self._update_task(
                            task_id,
                            {
                                "state": "running",
                                "status": "下载中",
                                "progress": max(0, min(progress, 100)),
                                "speed": f"{speed_kb:.1f} KB/s",
                                "writtenBytes": total_written,
                                "totalBytes": total,
                                "eta": eta,
                                "elapsedMs": int(elapsed * 1000),
                            },
                        )
                        now = time.time()
                        if now - window_start >= 1.0:
                            window_start = now
                            window_bytes = 0
        finally:
            with self._lock:
                self._cancelled.discard(task_id)

        if target.exists():
            target = self._unique_path(target)
        partial.replace(target)
        elapsed_ms = int((time.time() - start_at) * 1000)
        self._update_task(
            task_id,
            {
                "state": "completed",
                "status": "下载完成",
                "progress": 100,
                "speed": "0 KB/s",
                "writtenBytes": total_written,
                "totalBytes": total if total else total_written,
                "eta": "-",
                "elapsedMs": elapsed_ms,
                "finishedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "savePath": str(target),
                "fileName": target.name,
                "partialPath": "",
            },
        )
        self._log.info("download.complete", "下载完成", taskId=task_id, targetName=target.name, bytes=total_written)
        return f"下载完成: {target.name}"

    def _throttle(self, window_bytes: int, window_start: float) -> None:
        limit = self._speed_limit_kbps
        if limit <= 0:
            return
        expected = window_bytes / max(limit * 1024, 1)
        actual = time.time() - window_start
        if expected > actual:
            time.sleep(min(expected - actual, 0.5))

    def _worker_done(self, task_id: str) -> None:
        should_emit = False
        with self._lock:
            self._task_handles.pop(task_id, None)
            for task in self._tasks:
                if task.get("id") != task_id:
                    continue
                if task.get("state") == "pausing":
                    task.update({"state": "paused", "status": "已暂停", "speed": "0 KB/s"})
                    self._persist_task(task)
                    should_emit = True
                elif task.get("state") == "cancelling":
                    task.update({"state": "cancelled", "status": "已取消", "speed": "0 KB/s"})
                    self._persist_task(task)
                    should_emit = True
                    break
        if should_emit:
            self._emit_tasks()
        self._dispatch_queue()

    def _handle_download_error(self, task_id: str, exc: BaseException) -> None:
        message = str(exc)
        task = self._snapshot_task(task_id)
        if self._should_auto_retry(task, exc):
            attempts = int(task.get("attempts") or 0) if task is not None else 0
            retry_limit = _sanitize_retry_limit(_task_option(task, "retryLimit", self._retry_limit)) if task is not None else self._retry_limit
            self._update_task(
                task_id,
                {
                    "state": "queued",
                    "status": f"等待重试 {attempts}/{retry_limit}",
                    "speed": "0 KB/s",
                    "eta": "-",
                    "error": message,
                },
            )
            self._log.warning(
                "download.retry_scheduled",
                "下载失败，已安排自动重试",
                taskId=task_id,
                attempt=attempts,
                retryLimit=retry_limit,
                error=message,
            )
            self._on_download_finished(f"下载失败，自动重试 {attempts}/{retry_limit}: {message}")
            return
        self._update_task(
            task_id,
            {
                "state": "failed",
                "status": "下载失败",
                "speed": "0 KB/s",
                "eta": "-",
                "error": message,
            },
        )
        self._log.warning("download.failed", "下载失败", taskId=task_id, error=message)
        self._on_download_finished(f"下载失败: {message}")

    def _should_auto_retry(self, task: dict | None, exc: BaseException) -> bool:
        if task is None:
            return False
        task_id = str(task.get("id") or "")
        if not task_id or self._is_cancelled(task_id):
            return False
        if task.get("state") in {"paused", "pausing", "cancelled", "cancelling"}:
            return False
        retry_limit = _sanitize_retry_limit(_task_option(task, "retryLimit", self._retry_limit))
        attempts = int(task.get("attempts") or 0)
        return retry_limit > 0 and attempts <= retry_limit and _is_retryable_error(exc)

    def _update_task(self, task_id: str, data: dict) -> None:
        changed: dict | None = None
        with self._lock:
            for task in self._tasks:
                if task.get("id") == task_id:
                    task.update(data)
                    changed = dict(task)
                    break
        if changed is not None:
            self._persist_task(changed)
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
            return task_id in self._cancelled or task_id in self._paused

    def _is_paused(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self._paused

    def _find_existing_url(self, url: str) -> dict | None:
        clean = str(url or "").strip()
        if not clean:
            return None
        with self._lock:
            for task in self._tasks:
                if str(task.get("url") or "").strip() == clean:
                    return dict(task)
        return None

    def _persist_settings(self) -> None:
        if self._repository is None:
            return
        self._repository.save_settings(self.settings())

    def _persist_task(self, task: dict) -> None:
        if self._repository is None:
            return
        self._repository.upsert_task(task)

    def _network_snapshot(self) -> dict:
        return {
            "timeoutSec": self._timeout_sec,
            "retryLimit": self._retry_limit,
            "proxyUrl": self._proxy_url,
            "userAgent": self._user_agent,
            "referer": self._referer,
            "cookie": self._cookie,
            "customHeaders": self._custom_headers,
        }

    @staticmethod
    def _remove_partial(target: Path) -> None:
        try:
            if target.exists():
                target.unlink()
        except OSError:
            pass

    @staticmethod
    def _unique_path(target: Path) -> Path:
        if not target.exists() and not target.with_name(f"{target.name}.part").exists():
            return target
        stem = target.stem
        suffix = target.suffix
        parent = target.parent
        counter = 1
        while True:
            candidate = parent / f"{stem}_{counter}{suffix}"
            if not candidate.exists() and not candidate.with_name(f"{candidate.name}.part").exists():
                return candidate
            counter += 1


def _extract_urls(text: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"https?://[^\s'\"<>]+", str(text or ""), flags=re.IGNORECASE):
        candidate = match.group(0).rstrip(".,;)")
        if not candidate:
            continue
        if candidate not in seen:
            seen.add(candidate)
            urls.append(candidate)
    return urls


def _headers_for_task(task: dict, existing: int) -> dict[str, str]:
    headers = _parse_custom_headers(str(task.get("customHeaders") or ""))
    user_agent = str(task.get("userAgent") or "").strip()
    referer = str(task.get("referer") or "").strip()
    cookie = str(task.get("cookie") or "").strip()
    if user_agent:
        headers["User-Agent"] = user_agent
    if referer:
        headers["Referer"] = referer
    if cookie:
        headers["Cookie"] = cookie
    if existing > 0:
        headers["Range"] = f"bytes={existing}-"
    return headers


def _task_option(task: dict | None, key: str, default: object) -> object:
    if task is None:
        return default
    value = task.get(key)
    return default if value is None or value == "" else value


def _parse_custom_headers(value: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in str(value or "").splitlines():
        clean = line.strip()
        if not clean or ":" not in clean:
            continue
        name, raw = clean.split(":", 1)
        key = name.strip()
        if not key or not _valid_header_name(key):
            continue
        headers[key] = raw.strip()
    return headers


def _valid_header_name(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9!#$%&'*+.^_`|~-]+", value))


def _proxies_for_task(task: dict) -> dict[str, str] | None:
    proxy_url = _normalize_proxy_url(str(task.get("proxyUrl") or ""))
    if not proxy_url:
        return None
    return {"http": proxy_url, "https": proxy_url}


def _normalize_proxy_url(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "://" not in text:
        text = f"http://{text}"
    parsed = urlparse(text)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return ""
    return text


def _sanitize_timeout_sec(value: object) -> int:
    try:
        number = int(value or DEFAULT_TIMEOUT_SEC)
    except (TypeError, ValueError):
        number = DEFAULT_TIMEOUT_SEC
    return max(1, min(number, MAX_TIMEOUT_SEC))


def _sanitize_retry_limit(value: object) -> int:
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        number = DEFAULT_RETRY_LIMIT
    return max(0, min(number, MAX_RETRY_LIMIT))


def _is_retryable_error(exc: BaseException) -> bool:
    try:
        import requests
    except Exception:
        return True
    if isinstance(exc, requests.HTTPError):
        response = getattr(exc, "response", None)
        status_code = int(getattr(response, "status_code", 0) or 0)
        return status_code in {408, 425, 429} or 500 <= status_code < 600
    return isinstance(
        exc,
        (
            requests.ConnectionError,
            requests.Timeout,
            requests.ChunkedEncodingError,
            requests.ContentDecodingError,
        ),
    )


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


def _category_from_filename(name: str) -> str:
    suffix = Path(name).suffix.lower().lstrip(".")
    if suffix in {"zip", "rar", "7z", "tar", "gz", "bz2", "xz", "dmg", "iso"}:
        return "archive"
    if suffix in {"mp4", "mkv", "mov", "avi", "wmv", "flv", "webm", "m4v"}:
        return "video"
    if suffix in {"mp3", "wav", "flac", "aac", "ogg", "m4a"}:
        return "audio"
    if suffix in {"jpg", "jpeg", "png", "gif", "webp", "bmp", "svg", "heic"}:
        return "image"
    if suffix in {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "md", "csv"}:
        return "document"
    if suffix in {"exe", "msi", "pkg", "appimage", "deb", "rpm"}:
        return "program"
    return "other"


def state_label_for_persisted(state: str) -> str:
    if state == "queued":
        return "排队中"
    if state == "running":
        return "下载中"
    if state == "paused":
        return "已暂停"
    if state == "completed":
        return "下载完成"
    if state == "failed":
        return "下载失败"
    if state == "cancelled":
        return "已取消"
    return "等待"


def _total_size_from_response(resp: object, existing: int) -> int:
    content_range = str(getattr(resp, "headers", {}).get("content-range", ""))
    match = re.search(r"/(\d+)$", content_range)
    if match:
        return int(match.group(1))
    try:
        length = int(getattr(resp, "headers", {}).get("content-length", "0") or "0")
    except ValueError:
        length = 0
    if getattr(resp, "status_code", 0) == 206:
        return existing + length
    return length


def _format_eta(seconds: float) -> str:
    if seconds <= 0:
        return "-"
    value = int(seconds)
    if value < 60:
        return f"{value}s"
    minutes = value // 60
    if minutes < 60:
        return f"{minutes}m {value % 60}s"
    hours = minutes // 60
    return f"{hours}h {minutes % 60}m"


def _path_from_ui(value: str) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.startswith("file:///"):
        path_text = unquote(urlparse(text).path)
        if re.match(r"^/[A-Za-z]:/", path_text):
            path_text = path_text[1:]
        return Path(path_text)
    if text.startswith("file:"):
        path_text = unquote(urlparse(text).path)
        if re.match(r"^/[A-Za-z]:/", path_text):
            path_text = path_text[1:]
        return Path(path_text)
    return Path(text)


def _remove_path(value: str) -> None:
    if not value:
        return
    try:
        target = Path(value)
        if target.exists():
            target.unlink()
    except OSError:
        pass

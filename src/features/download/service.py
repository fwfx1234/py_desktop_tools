from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Callable

import requests

from app.qt.task_runner import TaskRunner


class DownloadService:
    def __init__(
        self,
        on_tasks_updated: Callable[[list[dict]], None],
        on_download_finished: Callable[[str], None],
    ) -> None:
        self._on_tasks_updated = on_tasks_updated
        self._on_download_finished = on_download_finished
        self._tasks: list[dict] = []
        self._cancelled: set[str] = set()
        self._runner = TaskRunner()

    def download_file(self, url: str, save_path: str) -> None:
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "url": url,
            "savePath": save_path,
            "status": "下载中",
            "progress": 0,
            "speed": "0 KB/s",
        }
        self._tasks.append(task)
        self._emit_tasks()
        self._runner.start(
            lambda: self._download_worker(task_id, url, save_path),
            on_success=lambda message: self._on_download_finished(str(message or "")),
            on_error=lambda exc: self._handle_download_error(task_id, exc),
        )

    def clear_tasks(self) -> None:
        self._tasks = []
        self._emit_tasks()

    def cancel_task(self, task_id: str) -> None:
        clean_id = str(task_id or "")
        if not clean_id:
            return
        self._cancelled.add(clean_id)
        self._update_task_in_main(clean_id, {"status": "正在取消", "speed": "0 KB/s"})

    def close(self) -> None:
        self._cancelled.update(str(task.get("id") or "") for task in self._tasks)
        self._runner.cancel_all()

    def _download_worker(self, task_id: str, url: str, save_path: str) -> str:
        target = Path(save_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        try:
            with requests.get(url, stream=True, timeout=30) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", "0") or "0")
                start_at = time.time()
                with target.open("wb") as file_obj:
                    for chunk in resp.iter_content(chunk_size=1024 * 64):
                        if self._is_cancelled(task_id):
                            self._remove_partial(target)
                            self._update_task(task_id, {"status": "已取消", "progress": 0, "speed": "0 KB/s"})
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
                            },
                        )
        finally:
            self._cancelled.discard(task_id)
        size_text = f"{written/1024:.1f}KB"
        if "total" in locals() and total > 0:
            size_text = f"{written/1024:.1f}KB / {total/1024:.1f}KB"
        self._update_task(task_id, {"status": "下载完成", "progress": 100, "speed": "0 KB/s"})
        return f"下载完成: {target.name} ({size_text})"

    def _handle_download_error(self, task_id: str, exc: BaseException) -> None:
        self._update_task(task_id, {"status": f"下载失败: {exc}", "speed": "0 KB/s"})
        self._on_download_finished(f"下载失败: {exc}")

    def _update_task(self, task_id: str, data: dict) -> None:
        self._runner.post(lambda: self._update_task_in_main(task_id, data))

    def _update_task_in_main(self, task_id: str, data: dict) -> None:
        for task in self._tasks:
            if task.get("id") == task_id:
                task.update(data)
                break
        self._emit_tasks()

    def _emit_tasks(self) -> None:
        self._on_tasks_updated([dict(task) for task in self._tasks])

    def _is_cancelled(self, task_id: str) -> bool:
        return task_id in self._cancelled

    @staticmethod
    def _remove_partial(target: Path) -> None:
        try:
            if target.exists():
                target.unlink()
        except OSError:
            pass

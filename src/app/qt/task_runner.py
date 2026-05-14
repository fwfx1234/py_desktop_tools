from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


TaskFunction = Callable[[], object]
TaskCallback = Callable[[object], None]
TaskErrorCallback = Callable[[BaseException], None]
TaskDoneCallback = Callable[[], None]


class TaskRunner(QObject):
    _finished = Signal(str, object, object)
    _posted = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pool = QThreadPool.globalInstance()
        self._callbacks: dict[str, tuple[TaskCallback | None, TaskErrorCallback | None, TaskDoneCallback | None]] = {}
        self._cancelled: set[str] = set()
        self._finished.connect(self._handle_finished)
        self._posted.connect(self._handle_posted)

    def start(
        self,
        fn: TaskFunction,
        *,
        on_success: TaskCallback | None = None,
        on_error: TaskErrorCallback | None = None,
        on_done: TaskDoneCallback | None = None,
    ) -> str:
        task_id = uuid4().hex
        self._callbacks[task_id] = (on_success, on_error, on_done)
        self._pool.start(_TaskRunnable(task_id, fn, self._finished))
        return task_id

    def cancel(self, task_id: str) -> None:
        self._cancelled.add(task_id)
        self._callbacks.pop(task_id, None)

    def cancel_all(self) -> None:
        self._cancelled.update(self._callbacks)
        self._callbacks.clear()

    def post(self, fn: Callable[[], None]) -> None:
        self._posted.emit(fn)

    @Slot(str, object, object)
    def _handle_finished(self, task_id: str, result: object, error: object) -> None:
        callbacks = self._callbacks.pop(task_id, None)
        if callbacks is None:
            self._cancelled.discard(task_id)
            return
        on_success, on_error, on_done = callbacks
        try:
            if task_id in self._cancelled:
                return
            if error is not None:
                if on_error is not None:
                    on_error(error if isinstance(error, BaseException) else RuntimeError(str(error)))
            elif on_success is not None:
                on_success(result)
        finally:
            self._cancelled.discard(task_id)
            if on_done is not None:
                on_done()

    @Slot(object)
    def _handle_posted(self, fn: object) -> None:
        if callable(fn):
            fn()


class _TaskRunnable(QRunnable):
    def __init__(self, task_id: str, fn: TaskFunction, finished_signal: Signal) -> None:
        super().__init__()
        self._task_id = task_id
        self._fn = fn
        self._finished_signal = finished_signal

    def run(self) -> None:
        try:
            result = self._fn()
            self._finished_signal.emit(self._task_id, result, None)
        except BaseException as exc:
            self._finished_signal.emit(self._task_id, None, exc)

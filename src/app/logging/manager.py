from __future__ import annotations

import atexit
import json
import logging
import os
import sys
import threading
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

from app.paths import data_dir

from .context import get_context, make_request_id, make_session_id, make_task_id, make_trace_id
from .redaction import preview_text, redact_mapping


_MANAGER: "LoggingManager | None" = None


class StructuredLogger:
    def __init__(self, manager: "LoggingManager", logger: logging.Logger, static_fields: dict[str, Any] | None = None) -> None:
        self._manager = manager
        self._logger = logger
        self._static_fields = dict(static_fields or {})

    def bind(self, **fields: Any) -> "StructuredLogger":
        merged = dict(self._static_fields)
        merged.update({key: value for key, value in fields.items() if value is not None and value != ""})
        return StructuredLogger(self._manager, self._logger, merged)

    def debug(self, event: str, message: str = "", **data: Any) -> None:
        self._log(logging.DEBUG, event, message, data)

    def info(self, event: str, message: str = "", **data: Any) -> None:
        self._log(logging.INFO, event, message, data)

    def warning(self, event: str, message: str = "", **data: Any) -> None:
        self._log(logging.WARNING, event, message, data)

    def error(self, event: str, message: str = "", **data: Any) -> None:
        self._log(logging.ERROR, event, message, data)

    def exception(self, event: str, message: str = "", **data: Any) -> None:
        self._log(logging.ERROR, event, message, data, exc_info=True)

    def log(self, level: int, event: str, message: str = "", **data: Any) -> None:
        self._log(level, event, message, data)

    def isEnabledFor(self, level: int) -> bool:
        return self._logger.isEnabledFor(level)

    def _log(self, level: int, event: str, message: str, data: dict[str, Any], *, exc_info: bool = False) -> None:
        if not self._logger.isEnabledFor(level):
            return
        payload = redact_mapping(data)
        fields = self._manager.collect_fields(self._static_fields)
        text = message or event
        self._logger.log(
            level,
            text,
            extra={
                "app_log_event": event,
                "app_log_message": text,
                "app_log_data": payload,
                "app_log_fields": fields,
                **{key: value for key, value in self._static_fields.items() if value is not None and value != ""},
            },
            exc_info=exc_info,
        )


class StructuredJsonFormatter(logging.Formatter):
    def __init__(self, app_name: str, app_version: str) -> None:
        super().__init__()
        self._app_name = app_name
        self._app_version = app_version

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).astimezone().isoformat(timespec="milliseconds")
        payload = {
            "ts": ts,
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "app_log_event", record.getMessage()),
            "message": getattr(record, "app_log_message", record.getMessage()),
            "app": self._app_name,
            "appVersion": self._app_version,
            "pid": os.getpid(),
            "thread": record.threadName,
            "module": record.module,
            "file": record.filename,
            "line": record.lineno,
            "func": record.funcName,
            "context": redact_mapping(get_context()),
            "fields": redact_mapping(getattr(record, "app_log_fields", {})),
            "data": redact_mapping(getattr(record, "app_log_data", {})),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class StructuredConsoleFormatter(logging.Formatter):
    def __init__(self, app_name: str, app_version: str) -> None:
        super().__init__()
        self._app_name = app_name
        self._app_version = app_version

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        message = getattr(record, "app_log_message", record.getMessage())
        text = preview_text(message, limit=120)
        extra = redact_mapping(getattr(record, "app_log_data", {}))
        if extra:
            text = f"{text} {extra}"
        return f"{ts} {record.levelname} [{record.name}] {text}"


class _LevelFilter(logging.Filter):
    def __init__(self, minimum_level: int) -> None:
        super().__init__()
        self._minimum_level = minimum_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= self._minimum_level


class LoggingManager:
    def __init__(
        self,
        *,
        app_name: str,
        app_version: str,
        log_dir: Path | None = None,
        level: str | int = "INFO",
        console: bool = True,
        retention_days: int = 7,
        file_level: str | int | None = None,
        qt_level: str | int | None = None,
    ) -> None:
        self.app_name = app_name
        self.app_version = app_version
        env_log_dir = os.getenv("PY_DESKTOP_TOOLS_LOG_DIR", "").strip()
        self.log_dir = Path(env_log_dir).expanduser() if env_log_dir else (log_dir or (data_dir() / "logs"))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = max(1, int(retention_days))
        self.level = self._resolve_level(level)
        self.file_level = self._resolve_level(file_level if file_level is not None else os.getenv("PY_DESKTOP_TOOLS_LOG_FILE_LEVEL", "WARNING"))
        self.qt_level = self._resolve_level(qt_level if qt_level is not None else os.getenv("PY_DESKTOP_TOOLS_QT_LOG_LEVEL", "WARNING"))
        self._plugin_handlers: dict[str, logging.Handler] = {}
        self._root_handlers: list[logging.Handler] = []
        self._qt_handler: logging.Handler | None = None
        self._configured = False
        self._console_enabled = console
        self._configure()

    def get_logger(self, name: str, *, plugin_id: str | None = None) -> StructuredLogger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = True
        inferred_plugin_id = plugin_id or self._infer_plugin_id(name)
        if inferred_plugin_id:
            self._ensure_plugin_handler(inferred_plugin_id, logger)
        return StructuredLogger(self, logger)

    def for_plugin(self, plugin_id: str, name: str | None = None) -> StructuredLogger:
        logger_name = name or f"plugin.{self._safe_part(plugin_id)}"
        return self.get_logger(logger_name, plugin_id=plugin_id).bind(pluginId=plugin_id)

    def bind_context(self, **fields: Any):
        from .context import bind_context

        return bind_context(**fields)

    def collect_fields(self, static_fields: dict[str, Any] | None = None) -> dict[str, Any]:
        fields = dict(get_context())
        if static_fields:
            fields.update({key: value for key, value in static_fields.items() if value is not None and value != ""})
        return fields

    def install_qt_message_handler(self) -> None:
        if self._qt_handler is not None:
            return
        try:
            from PySide6.QtCore import QtMsgType, qInstallMessageHandler
        except Exception:
            return

        qt_logger = logging.getLogger("qt")
        qt_logger.setLevel(logging.DEBUG)
        qt_logger.propagate = True
        handler = self._create_file_handler("qt.log", level=self.qt_level)
        qt_logger.addHandler(handler)
        self._qt_handler = handler

        def _handler(mode, context, message):
            level = self._qt_level(mode)
            if level < self.qt_level:
                return
            extra = {
                "app_log_event": "qt.message",
                "app_log_message": str(message),
                "app_log_data": {
                    "category": getattr(context, "category", ""),
                    "file": getattr(context, "file", ""),
                    "line": getattr(context, "line", 0),
                    "function": getattr(context, "function", ""),
                },
                "app_log_fields": {},
            }
            qt_logger.log(level, str(message), extra=extra)

        qInstallMessageHandler(_handler)

    def install_excepthooks(self) -> None:
        def _sys_hook(exc_type, exc, tb):
            logging.getLogger("app.unhandled").critical(
                "未捕获异常",
                exc_info=(exc_type, exc, tb),
                extra={
                    "app_log_event": "app.unhandled_exception",
                    "app_log_message": "未捕获异常",
                    "app_log_data": {},
                    "app_log_fields": self.collect_fields(),
                },
            )

        def _thread_hook(args):
            logging.getLogger("app.thread").error(
                "线程异常",
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
                extra={
                    "app_log_event": "thread.unhandled_exception",
                    "app_log_message": "线程异常",
                    "app_log_data": {"threadName": getattr(args.thread, "name", "")},
                    "app_log_fields": self.collect_fields(),
                },
            )

        sys.excepthook = _sys_hook
        if hasattr(threading, "excepthook"):
            threading.excepthook = _thread_hook  # type: ignore[assignment]

    def shutdown(self) -> None:
        root = logging.getLogger()
        for handler in list(self._root_handlers):
            try:
                root.removeHandler(handler)
            except Exception:
                pass
            handler.close()
        self._root_handlers.clear()
        for handler in self._plugin_handlers.values():
            handler.close()
        self._plugin_handlers.clear()
        if self._qt_handler is not None:
            self._qt_handler.close()
            self._qt_handler = None

    def _configure(self) -> None:
        if self._configured:
            return
        root = logging.getLogger()
        for handler in list(root.handlers):
            root.removeHandler(handler)
            handler.close()
        root.setLevel(logging.DEBUG)

        if self._console_enabled:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.level)
            console_handler.setFormatter(StructuredConsoleFormatter(self.app_name, self.app_version))
            root.addHandler(console_handler)
            self._root_handlers.append(console_handler)

        try:
            app_handler = self._create_file_handler("app.log", level=self.file_level)
            root.addHandler(app_handler)
            self._root_handlers.append(app_handler)

            error_handler = self._create_file_handler("error.log", level=logging.ERROR)
            error_handler.addFilter(_LevelFilter(logging.ERROR))
            root.addHandler(error_handler)
            self._root_handlers.append(error_handler)
        except Exception:
            fallback = logging.StreamHandler()
            fallback.setLevel(logging.DEBUG)
            fallback.setFormatter(StructuredConsoleFormatter(self.app_name, self.app_version))
            root.addHandler(fallback)
            self._root_handlers.append(fallback)

        self._install_record_factory()
        logging.captureWarnings(True)
        self.install_excepthooks()
        atexit.register(self.shutdown)
        self._configured = True

    def _create_file_handler(self, filename: str, *, level: int) -> logging.Handler:
        path = self.log_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = TimedRotatingFileHandler(
            path,
            when="midnight",
            backupCount=self.retention_days,
            encoding="utf-8",
            utc=False,
        )
        handler.setLevel(level)
        handler.setFormatter(StructuredJsonFormatter(self.app_name, self.app_version))
        return handler

    def _ensure_plugin_handler(self, plugin_id: str, logger: logging.Logger) -> None:
        safe_plugin_id = self._safe_part(plugin_id)
        if safe_plugin_id in self._plugin_handlers:
            if self._plugin_handlers[safe_plugin_id] not in logger.handlers:
                logger.addHandler(self._plugin_handlers[safe_plugin_id])
            return
        handler = self._create_file_handler(Path("plugins") / f"{safe_plugin_id}.log", level=self.file_level)
        self._plugin_handlers[safe_plugin_id] = handler
        logger.addHandler(handler)

    @staticmethod
    def _resolve_level(level: str | int) -> int:
        if isinstance(level, int):
            return level
        text = str(level or "").strip().upper()
        return getattr(logging, text, logging.INFO)

    @staticmethod
    def _infer_plugin_id(name: str) -> str | None:
        if not name.startswith("features."):
            return None
        parts = name.split(".")
        if len(parts) < 2:
            return None
        return parts[1].replace("_", "-")

    @staticmethod
    def _safe_part(value: str) -> str:
        return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value).strip("._") or "anonymous"

    @staticmethod
    def _qt_level(mode: Any) -> int:
        try:
            from PySide6.QtCore import QtMsgType
        except Exception:
            return logging.INFO
        if mode == QtMsgType.QtDebugMsg:
            return logging.DEBUG
        if mode == QtMsgType.QtInfoMsg:
            return logging.INFO
        if mode == QtMsgType.QtWarningMsg:
            return logging.WARNING
        if mode == QtMsgType.QtCriticalMsg:
            return logging.ERROR
        if hasattr(QtMsgType, "QtFatalMsg") and mode == QtMsgType.QtFatalMsg:
            return logging.CRITICAL
        return logging.INFO

    def _install_record_factory(self) -> None:
        current_factory = logging.getLogRecordFactory()

        def _factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            record = current_factory(*args, **kwargs)
            context = get_context()
            for key, value in context.items():
                if not hasattr(record, key):
                    setattr(record, key, value)
            return record

        logging.setLogRecordFactory(_factory)


def init_logging(
    *,
    app_name: str = "py-desktop-tools",
    app_version: str = "unknown",
    log_dir: Path | None = None,
    level: str | int = "INFO",
    console: bool = True,
    retention_days: int = 7,
    file_level: str | int | None = None,
    qt_level: str | int | None = None,
) -> LoggingManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = LoggingManager(
            app_name=app_name,
            app_version=app_version,
            log_dir=log_dir,
            level=level,
            console=console,
            retention_days=retention_days,
            file_level=file_level,
            qt_level=qt_level,
        )
    return _MANAGER


def get_logger(name: str, *, plugin_id: str | None = None) -> StructuredLogger:
    manager = _MANAGER or init_logging()
    return manager.get_logger(name, plugin_id=plugin_id)


def for_plugin(plugin_id: str, name: str | None = None) -> StructuredLogger:
    manager = _MANAGER or init_logging()
    return manager.for_plugin(plugin_id, name=name)


def bind_context(**fields: Any):
    manager = _MANAGER or init_logging()
    return manager.bind_context(**fields)


def install_qt_message_handler() -> None:
    manager = _MANAGER or init_logging()
    manager.install_qt_message_handler()


def make_ids() -> dict[str, str]:
    return {
        "traceId": make_trace_id(),
        "sessionId": make_session_id(),
        "requestId": make_request_id(),
        "taskId": make_task_id(),
    }

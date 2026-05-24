from __future__ import annotations

import os
from typing import Any

from app.storage import StorageManager


PLUGIN_SESSION_SETTINGS_NAMESPACE = "plugins/session"
PLUGIN_WINDOW_RETENTION_MS_KEY = "windowRetentionMs"
STANDARD_PLUGIN_WINDOW_RETENTION_MS = 5 * 60 * 1000
MIN_PLUGIN_WINDOW_RETENTION_MS = 1_000
MAX_PLUGIN_WINDOW_RETENTION_MS = 60 * 60 * 1000


def plugin_window_retention_ms(storage: object | None = None) -> int:
    raw = os.getenv("PY_DESKTOP_PLUGIN_RETENTION_MS", "").strip()
    if raw:
        return _coerce_retention_ms(raw, STANDARD_PLUGIN_WINDOW_RETENTION_MS)
    store = _settings_store(storage)
    if store is None:
        return STANDARD_PLUGIN_WINDOW_RETENTION_MS
    return _coerce_retention_ms(
        store.get(PLUGIN_WINDOW_RETENTION_MS_KEY, STANDARD_PLUGIN_WINDOW_RETENTION_MS),
        STANDARD_PLUGIN_WINDOW_RETENTION_MS,
    )


def plugin_window_retention_seconds(storage: object | None = None) -> int:
    return max(1, round(plugin_window_retention_ms(storage) / 1000))


def set_plugin_window_retention_seconds(storage: object | None, seconds: object) -> int:
    value = _coerce_retention_ms(
        _coerce_int(seconds, round(STANDARD_PLUGIN_WINDOW_RETENTION_MS / 1000)) * 1000,
        STANDARD_PLUGIN_WINDOW_RETENTION_MS,
    )
    store = _settings_store(storage)
    if store is not None:
        store.set(PLUGIN_WINDOW_RETENTION_MS_KEY, value)
    return value


def restore_standard_plugin_window_retention(storage: object | None) -> int:
    store = _settings_store(storage)
    if store is not None:
        store.set(PLUGIN_WINDOW_RETENTION_MS_KEY, STANDARD_PLUGIN_WINDOW_RETENTION_MS)
    return STANDARD_PLUGIN_WINDOW_RETENTION_MS


def _settings_store(storage: object | None):
    if not isinstance(storage, StorageManager):
        return None
    return storage.dict_store(
        PLUGIN_SESSION_SETTINGS_NAMESPACE,
        defaults={PLUGIN_WINDOW_RETENTION_MS_KEY: STANDARD_PLUGIN_WINDOW_RETENTION_MS},
    )


def _coerce_retention_ms(value: Any, default: int) -> int:
    raw = _coerce_int(value, default)
    return min(MAX_PLUGIN_WINDOW_RETENTION_MS, max(MIN_PLUGIN_WINDOW_RETENTION_MS, raw))


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

"""SQLite runtime tuning and retry helpers."""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Callable, TypeVar


T = TypeVar("T")

DEFAULT_BUSY_TIMEOUT_MS = 30000
DEFAULT_WRITE_RETRY_ATTEMPTS = 4
DEFAULT_WRITE_RETRY_BASE_MS = 50


def env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, "")
    try:
        value = int(raw) if raw.strip() else default
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


def sqlite_busy_timeout_ms() -> int:
    return env_int("VAULT_SQLITE_BUSY_TIMEOUT_MS", DEFAULT_BUSY_TIMEOUT_MS, minimum=0, maximum=300000)


def sqlite_write_retry_attempts() -> int:
    return env_int("VAULT_SQLITE_WRITE_RETRY_ATTEMPTS", DEFAULT_WRITE_RETRY_ATTEMPTS, minimum=1, maximum=20)


def sqlite_write_retry_base_ms() -> int:
    return env_int("VAULT_SQLITE_WRITE_RETRY_BASE_MS", DEFAULT_WRITE_RETRY_BASE_MS, minimum=0, maximum=5000)


def connect_sqlite(db_path: str | Path) -> sqlite3.Connection:
    busy_ms = sqlite_busy_timeout_ms()
    conn = sqlite3.connect(str(db_path), timeout=max(0.0, busy_ms / 1000.0))
    configure_sqlite_connection(conn, busy_timeout_ms=busy_ms)
    return conn


def configure_sqlite_connection(conn: sqlite3.Connection, *, busy_timeout_ms: int | None = None) -> None:
    busy_ms = sqlite_busy_timeout_ms() if busy_timeout_ms is None else busy_timeout_ms
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(f"PRAGMA busy_timeout={max(0, int(busy_ms))}")
    conn.execute("PRAGMA wal_autocheckpoint=1000")


def is_sqlite_locked_error(exc: BaseException) -> bool:
    if not isinstance(exc, sqlite3.OperationalError):
        return False
    message = str(exc).lower()
    return "database is locked" in message or "database table is locked" in message or "database is busy" in message


def sqlite_write_with_retry(
    operation: Callable[[], T],
    *,
    attempts: int | None = None,
    base_delay_ms: int | None = None,
    rollback: Callable[[], object] | None = None,
) -> T:
    max_attempts = sqlite_write_retry_attempts() if attempts is None else max(1, int(attempts))
    delay_ms = sqlite_write_retry_base_ms() if base_delay_ms is None else max(0, int(base_delay_ms))
    last_exc: sqlite3.OperationalError | None = None
    for attempt in range(max_attempts):
        try:
            return operation()
        except sqlite3.OperationalError as exc:
            if not is_sqlite_locked_error(exc) or attempt >= max_attempts - 1:
                raise
            last_exc = exc
            if rollback is not None:
                try:
                    rollback()
                except sqlite3.Error:
                    pass
            if delay_ms:
                time.sleep((delay_ms * (2**attempt)) / 1000.0)
    if last_exc is not None:
        raise last_exc
    return operation()

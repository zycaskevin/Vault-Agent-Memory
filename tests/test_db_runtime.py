"""SQLite runtime tuning and retry tests."""

from __future__ import annotations

import sqlite3

import pytest

from vault.db import VaultDB
from vault.db_runtime import is_sqlite_locked_error, sqlite_write_with_retry


def test_vaultdb_connect_applies_busy_timeout_from_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_SQLITE_BUSY_TIMEOUT_MS", "12345")

    with VaultDB(tmp_path / "vault.db") as db:
        busy_timeout = db.conn.execute("PRAGMA busy_timeout").fetchone()[0]
        journal_mode = str(db.conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        synchronous = int(db.conn.execute("PRAGMA synchronous").fetchone()[0])

    assert busy_timeout == 12345
    assert journal_mode == "wal"
    assert synchronous == 1  # NORMAL


def test_sqlite_write_with_retry_retries_locked_errors(monkeypatch):
    monkeypatch.setenv("VAULT_SQLITE_WRITE_RETRY_ATTEMPTS", "3")
    monkeypatch.setenv("VAULT_SQLITE_WRITE_RETRY_BASE_MS", "0")
    calls = {"write": 0, "rollback": 0}

    def write():
        calls["write"] += 1
        if calls["write"] < 3:
            raise sqlite3.OperationalError("database is locked")
        return "ok"

    def rollback():
        calls["rollback"] += 1

    assert sqlite_write_with_retry(write, rollback=rollback) == "ok"
    assert calls == {"write": 3, "rollback": 2}


def test_sqlite_write_with_retry_does_not_retry_unrelated_operational_errors(monkeypatch):
    monkeypatch.setenv("VAULT_SQLITE_WRITE_RETRY_ATTEMPTS", "3")
    calls = {"write": 0}

    def write():
        calls["write"] += 1
        raise sqlite3.OperationalError("no such table: knowledge")

    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        sqlite_write_with_retry(write)

    assert calls["write"] == 1


def test_is_sqlite_locked_error_matches_common_lock_messages():
    assert is_sqlite_locked_error(sqlite3.OperationalError("database is locked"))
    assert is_sqlite_locked_error(sqlite3.OperationalError("database table is locked"))
    assert is_sqlite_locked_error(sqlite3.OperationalError("database is busy"))
    assert not is_sqlite_locked_error(sqlite3.OperationalError("malformed match expression"))

"""SQLite storage. Only the daemon writes to this database."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    email TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL,
    locale TEXT NOT NULL DEFAULT 'en',
    password_hash TEXT NOT NULL,
    must_change_pw INTEGER NOT NULL DEFAULT 0,
    failed_logins INTEGER NOT NULL DEFAULT 0,
    locked_until REAL NOT NULL DEFAULT 0,
    disabled INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    last_login REAL
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at REAL NOT NULL,
    last_seen REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS targets (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    protocol TEXT NOT NULL,
    host TEXT NOT NULL DEFAULT '',
    port INTEGER,
    path TEXT NOT NULL DEFAULT '',
    username TEXT NOT NULL DEFAULT '',
    secret TEXT NOT NULL DEFAULT '',
    options TEXT NOT NULL DEFAULT '{}',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS file_index (
    path TEXT PRIMARY KEY,
    size INTEGER NOT NULL,
    mtime REAL NOT NULL,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL,
    uploaded INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS file_events (
    id INTEGER PRIMARY KEY,
    time REAL NOT NULL,
    path TEXT NOT NULL,
    event TEXT NOT NULL,
    size INTEGER,
    mtime REAL,
    spool_path TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS uploads (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES file_events(id) ON DELETE CASCADE,
    target_id INTEGER NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
    remote_path TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    next_try REAL NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    finished_at REAL
);

CREATE TABLE IF NOT EXISTS notify_rules (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    events TEXT NOT NULL,
    pattern TEXT NOT NULL DEFAULT '*',
    recipients TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'instant',
    digest_minutes INTEGER NOT NULL DEFAULT 60,
    enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS notify_items (
    id INTEGER PRIMARY KEY,
    rule_id INTEGER NOT NULL REFERENCES notify_rules(id) ON DELETE CASCADE,
    time REAL NOT NULL,
    event TEXT NOT NULL,
    path TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    sent INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS mail_queue (
    id INTEGER PRIMARY KEY,
    created_at REAL NOT NULL,
    recipients TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_try REAL NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT '',
    sent_at REAL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    time REAL NOT NULL,
    level TEXT NOT NULL,
    source TEXT NOT NULL,
    message TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    time REAL NOT NULL,
    user_id INTEGER,
    username TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL,
    object TEXT NOT NULL DEFAULT '',
    details TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_uploads_status ON uploads(status, next_try);
CREATE INDEX IF NOT EXISTS idx_uploads_event ON uploads(event_id);
CREATE INDEX IF NOT EXISTS idx_events_time ON events(time);
CREATE INDEX IF NOT EXISTS idx_file_events_time ON file_events(time);
CREATE INDEX IF NOT EXISTS idx_notify_items_rule ON notify_items(rule_id, sent);
"""


class Database:
    """Thin wrapper around sqlite3 with one connection per thread."""

    def __init__(self, path: Path | str):
        self.path = str(path)
        self._local = threading.local()
        self.write_lock = threading.RLock()

    def conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=30000")
            self._local.conn = conn
        return conn

    def migrate(self) -> None:
        conn = self.conn()
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(SCHEMA)
        self.set_setting("schema_version", SCHEMA_VERSION)

    def all(self, sql: str, params: tuple | list = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in self.conn().execute(sql, params).fetchall()]

    def one(self, sql: str, params: tuple | list = ()) -> dict[str, Any] | None:
        row = self.conn().execute(sql, params).fetchone()
        return dict(row) if row else None

    def scalar(self, sql: str, params: tuple | list = ()) -> Any:
        row = self.conn().execute(sql, params).fetchone()
        return row[0] if row else None

    def run(self, sql: str, params: tuple | list = ()) -> int:
        """Execute a statement and return lastrowid."""
        with self.write_lock:
            cur = self.conn().execute(sql, params)
            return cur.lastrowid or 0

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.write_lock:
            conn = self.conn()
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")

    # Settings are stored as JSON values.

    def get_setting(self, key: str, default: Any = None) -> Any:
        raw = self.scalar("SELECT value FROM settings WHERE key = ?", (key,))
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default

    def set_setting(self, key: str, value: Any) -> None:
        self.run(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)),
        )

    def get_dict_setting(self, key: str, defaults: dict[str, Any]) -> dict[str, Any]:
        stored = self.get_setting(key, {}) or {}
        merged = dict(defaults)
        merged.update({k: v for k, v in stored.items() if k in defaults})
        return merged

    # Logging helpers.

    def log(self, level: str, source: str, message: str) -> None:
        self.run(
            "INSERT INTO events(time, level, source, message) VALUES(?, ?, ?, ?)",
            (time.time(), level, source, message[:2000]),
        )

    def audit(self, user: dict | None, action: str, obj: str = "", details: str = "") -> None:
        self.run(
            "INSERT INTO audit_log(time, user_id, username, action, object, details) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (
                time.time(),
                user["id"] if user else None,
                user["username"] if user else "",
                action,
                obj,
                details[:2000],
            ),
        )

    def prune(self, keep_days: int = 90) -> None:
        cutoff = time.time() - keep_days * 86400
        with self.write_lock:
            conn = self.conn()
            conn.execute("DELETE FROM events WHERE time < ?", (cutoff,))
            conn.execute("DELETE FROM notify_items WHERE sent = 1 AND time < ?", (cutoff,))
            conn.execute("DELETE FROM mail_queue WHERE sent_at IS NOT NULL AND sent_at < ?", (cutoff,))
            conn.execute(
                "DELETE FROM file_events WHERE time < ? AND id NOT IN "
                "(SELECT event_id FROM uploads WHERE status = 'pending')",
                (cutoff,),
            )

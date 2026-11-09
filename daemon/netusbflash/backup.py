"""Backup and restore of the configuration.

A backup is a JSON document with all settings, targets, notification rules
and users (with password hashes). Stored passwords of targets and the SMTP
server are only included when a backup passphrase is given; they are then
encrypted with a key derived from that passphrase (scrypt + Fernet). Without
a passphrase they are left out and must be entered again after a restore.

Backups can be downloaded, restored, and uploaded on a schedule to a
directory on one of the upload targets.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import tempfile
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cryptography.fernet import Fernet, InvalidToken

from . import __version__
from .system import CommandError
from .transports import TransferError, join_remote, make_transport

if TYPE_CHECKING:
    from .service import Context

log = logging.getLogger(__name__)

FORMAT = "netusbflash-backup"
FORMAT_VERSION = 1
INTERVALS = ("daily", "weekly", "monthly")
DEFAULT_BACKUP: dict[str, Any] = {
    "enabled": False,
    "target_id": None,
    "directory": "netusbflash-backups",
    "interval": "daily",
    "hour": 3,
    "passphrase": "",          # stored encrypted with the device key
}
# Settings that describe the device's runtime state, not its configuration.
SKIP_SETTINGS = {"schema_version", "setup_completed", "setup_step", "index_initialized", "last_sync",
                 "update_info", "os_update_info", "backup_last"}
_SCRYPT = {"n": 2**15, "r": 8, "p": 1}


class BackupError(Exception):
    pass


def _key(passphrase: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    raw = hashlib.scrypt(passphrase.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=32, maxmem=128 * 1024 * 1024)
    return base64.urlsafe_b64encode(raw)


def encrypt_secrets(data: dict[str, Any], passphrase: str) -> dict[str, Any]:
    salt = secrets.token_bytes(16)
    token = Fernet(_key(passphrase, salt, **_SCRYPT)).encrypt(json.dumps(data).encode("utf-8"))
    return {"kdf": "scrypt", **_SCRYPT, "salt": base64.b64encode(salt).decode(), "token": token.decode()}


def decrypt_secrets(blob: dict[str, Any], passphrase: str) -> dict[str, Any]:
    try:
        key = _key(passphrase, base64.b64decode(blob["salt"]), int(blob["n"]), int(blob["r"]), int(blob["p"]))
        return json.loads(Fernet(key).decrypt(blob["token"].encode()).decode("utf-8"))
    except (InvalidToken, KeyError, ValueError, TypeError) as exc:
        raise BackupError("wrong_passphrase") from exc


def next_due(last: float | None, interval: str, hour: int, now: float) -> float:
    """Unix time of the next scheduled run after `last` (local time)."""
    lt = time.localtime(now)
    today = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, hour, 0, 0, 0, 0, -1))
    if last is None:
        return today if today >= now - 60 else today + 86400
    min_gap = {"daily": 20 * 3600, "weekly": 6.5 * 86400, "monthly": 27 * 86400}[interval]
    candidate = today
    while candidate <= last or candidate - last < min_gap:
        candidate += 86400
    if interval == "monthly":
        while time.localtime(candidate).tm_mday != 1:
            candidate += 86400
    return candidate


class BackupService(threading.Thread):
    def __init__(self, ctx: "Context"):
        super().__init__(name="backup", daemon=True)
        self.ctx = ctx
        self.stop_event = threading.Event()
        self.lock = threading.Lock()

    def settings(self) -> dict[str, Any]:
        return self.ctx.db.get_dict_setting("backup", DEFAULT_BACKUP)

    def status(self) -> dict[str, Any]:
        cfg = self.settings()
        last = self.ctx.db.get_setting("backup_last", {}) or {}
        public = {k: v for k, v in cfg.items() if k != "passphrase"}
        public["has_passphrase"] = bool(cfg["passphrase"])
        next_run = None
        if cfg["enabled"] and cfg["target_id"]:
            next_run = next_due(last.get("success_time"), cfg["interval"], int(cfg["hour"]), time.time())
        return {"settings": public, "last": last, "next_run": next_run}

    # Export ------------------------------------------------------------------

    def export(self, passphrase: str = "") -> dict[str, Any]:
        db = self.ctx.db
        settings = {}
        for row in db.all("SELECT key, value FROM settings"):
            if row["key"] in SKIP_SETTINGS:
                continue
            try:
                settings[row["key"]] = json.loads(row["value"])
            except json.JSONDecodeError:
                continue
        secret_values: dict[str, Any] = {"targets": {}, "smtp_password": "", "backup_passphrase": ""}
        smtp = settings.get("smtp")
        if isinstance(smtp, dict):
            secret_values["smtp_password"] = self.ctx.secrets.decrypt(smtp.get("password", ""))
            smtp["password"] = ""
        backup_cfg = settings.get("backup")
        if isinstance(backup_cfg, dict):
            secret_values["backup_passphrase"] = self.ctx.secrets.decrypt(backup_cfg.get("passphrase", ""))
            backup_cfg["passphrase"] = ""
        targets = []
        for row in db.all("SELECT * FROM targets ORDER BY id"):
            secret_values["targets"][str(row["id"])] = self.ctx.secrets.decrypt(row["secret"])
            row = dict(row)
            row.pop("secret", None)
            row["options"] = json.loads(row["options"] or "{}")
            targets.append(row)
        users = db.all("SELECT username, email, role, locale, password_hash, must_change_pw, disabled, created_at "
                       "FROM users ORDER BY id")
        rules = db.all("SELECT * FROM notify_rules ORDER BY id")
        return {
            "format": FORMAT,
            "format_version": FORMAT_VERSION,
            "app_version": __version__,
            "created": time.time(),
            "hostname": self.ctx.hostname(),
            "settings": settings,
            "targets": targets,
            "notify_rules": rules,
            "users": users,
            "secrets": encrypt_secrets(secret_values, passphrase) if passphrase else None,
        }

    def filename(self) -> str:
        return f"netusbflash-backup-{self.ctx.hostname()}-{time.strftime('%Y%m%d-%H%M%S')}.json"

    # Restore -----------------------------------------------------------------

    def restore(self, backup: dict[str, Any], passphrase: str = "") -> dict[str, Any]:
        if not isinstance(backup, dict) or backup.get("format") != FORMAT:
            raise BackupError("invalid_backup")
        if int(backup.get("format_version", 0)) > FORMAT_VERSION:
            raise BackupError("backup_too_new")
        users = backup.get("users") or []
        if not any(u.get("role") == "admin" and not u.get("disabled") for u in users):
            raise BackupError("backup_without_admin")
        secret_values: dict[str, Any] = {"targets": {}, "smtp_password": "", "backup_passphrase": ""}
        if backup.get("secrets"):
            if not passphrase:
                raise BackupError("passphrase_required")
            secret_values = decrypt_secrets(backup["secrets"], passphrase)
        db = self.ctx.db
        box = self.ctx.secrets
        with db.transaction() as conn:
            for key, value in (backup.get("settings") or {}).items():
                if key in SKIP_SETTINGS or not isinstance(key, str):
                    continue
                if key == "smtp" and isinstance(value, dict):
                    value["password"] = box.encrypt(secret_values.get("smtp_password", ""))
                if key == "backup" and isinstance(value, dict):
                    value["passphrase"] = box.encrypt(secret_values.get("backup_passphrase", ""))
                conn.execute("INSERT INTO settings(key, value) VALUES(?, ?) "
                             "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, json.dumps(value)))
            conn.execute("DELETE FROM targets")
            for t in backup.get("targets") or []:
                conn.execute(
                    "INSERT INTO targets(id, name, protocol, host, port, path, username, secret, options, enabled, "
                    "created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (int(t["id"]), str(t["name"]), str(t["protocol"]), str(t.get("host", "")), t.get("port"),
                     str(t.get("path", "")), str(t.get("username", "")),
                     box.encrypt(secret_values.get("targets", {}).get(str(t["id"]), "")),
                     json.dumps(t.get("options") or {}), int(bool(t.get("enabled", True))),
                     float(t.get("created_at") or time.time()), time.time()))
            conn.execute("DELETE FROM notify_rules")
            for r in backup.get("notify_rules") or []:
                conn.execute(
                    "INSERT INTO notify_rules(id, name, events, pattern, recipients, mode, digest_minutes, enabled, "
                    "subject_template, body_template) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (int(r["id"]), str(r["name"]), str(r["events"]), str(r.get("pattern", "*")),
                     str(r["recipients"]), str(r.get("mode", "instant")), int(r.get("digest_minutes", 60)),
                     int(bool(r.get("enabled", True))), str(r.get("subject_template", "")),
                     str(r.get("body_template", ""))))
            conn.execute("DELETE FROM sessions")
            conn.execute("DELETE FROM users")
            for u in users:
                conn.execute(
                    "INSERT INTO users(username, email, role, locale, password_hash, must_change_pw, disabled, "
                    "created_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                    (str(u["username"]), str(u.get("email", "")), str(u["role"]), str(u.get("locale", "en")),
                     str(u["password_hash"]), int(bool(u.get("must_change_pw"))), int(bool(u.get("disabled"))),
                     float(u.get("created_at") or time.time())))
        db.log("info", "backup", f"Configuration restored from a backup of {backup.get('hostname', '?')} "
                                 f"(version {backup.get('app_version', '?')})")
        return {"secrets_restored": bool(backup.get("secrets")), "targets": len(backup.get("targets") or []),
                "users": len(users)}

    # Scheduled upload --------------------------------------------------------

    def run_now(self) -> dict[str, Any]:
        with self.lock:
            cfg = self.settings()
            target = self.ctx.db.one("SELECT * FROM targets WHERE id = ?", (cfg["target_id"],)) if cfg["target_id"] else None
            last = self.ctx.db.get_setting("backup_last", {}) or {}
            now = time.time()
            if target is None:
                result = {"time": now, "ok": False, "error": "no_target"}
            else:
                result = self._upload(target, cfg, now)
            if result["ok"]:
                last.update(success_time=now)
            last.update(time=now, ok=result["ok"], error=result.get("error", ""), file=result.get("file", ""),
                        target=target["name"] if target else "")
            self.ctx.db.set_setting("backup_last", last)
            return self.status()

    def _upload(self, target: dict[str, Any], cfg: dict[str, Any], now: float) -> dict[str, Any]:
        passphrase = self.ctx.secrets.decrypt(cfg["passphrase"])
        data = json.dumps(self.export(passphrase), indent=1).encode("utf-8")
        name = self.filename()
        fd, tmp = tempfile.mkstemp(prefix="backup-", suffix=".json", dir=self.ctx.paths.spool)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            view = self.ctx.target_view(target)
            transport = make_transport(view, self.ctx.secrets.decrypt(target["secret"]), self.ctx.paths)
            remote = transport.put(Path(tmp), join_remote(cfg["directory"] or "", name))
        except (TransferError, CommandError, OSError) as exc:
            self.ctx.db.log("error", "backup", f"Backup upload to {target['name']} failed: {exc}")
            return {"ok": False, "error": str(exc)}
        finally:
            Path(tmp).unlink(missing_ok=True)
        self.ctx.db.log("info", "backup", f"Backup uploaded to {target['name']} ({remote})")
        return {"ok": True, "file": remote}

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        while not self.stop_event.wait(60):
            try:
                cfg = self.settings()
                if not cfg["enabled"] or not cfg["target_id"]:
                    continue
                last = self.ctx.db.get_setting("backup_last", {}) or {}
                due = next_due(last.get("success_time"), cfg["interval"], int(cfg["hour"]), time.time())
                # After a failure, retry at most once an hour.
                if time.time() >= due and time.time() - (last.get("time") or 0) > 3600:
                    self.run_now()
            except Exception:
                log.exception("scheduled backup failed")

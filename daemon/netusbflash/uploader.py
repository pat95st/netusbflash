"""Processes the upload queue: one row per (file event, target)."""

from __future__ import annotations

import logging
import shutil
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

from .system import CommandError
from .transports import TransferError, make_transport

if TYPE_CHECKING:
    from .service import Context

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 10
BATCH = 5


def backoff(attempts: int) -> float:
    """Seconds until the next try: 1, 2, 4 ... minutes, capped at 30 minutes."""
    return min(60 * (2 ** max(attempts - 1, 0)), 1800)


class Uploader(threading.Thread):
    def __init__(self, ctx: "Context"):
        super().__init__(name="uploader", daemon=True)
        self.ctx = ctx
        self.stop_event = threading.Event()
        self._wake = threading.Event()
        self.current: dict | None = None

    def wake(self) -> None:
        self._wake.set()

    def stop(self) -> None:
        self.stop_event.set()
        self._wake.set()

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                worked = self.process_batch()
            except Exception as exc:
                log.exception("upload batch failed")
                self.ctx.db.log("error", "upload", f"Uploader error: {exc}")
                worked = False
            if not worked:
                self._wake.wait(15)
                self._wake.clear()

    def process_batch(self) -> bool:
        rows = self.ctx.db.all(
            "SELECT u.*, e.path AS usb_path, e.spool_path FROM uploads u "
            "JOIN file_events e ON e.id = u.event_id "
            "WHERE u.status = 'pending' AND u.next_try <= ? ORDER BY u.id LIMIT ?",
            (time.time(), BATCH),
        )
        for row in rows:
            if self.stop_event.is_set():
                break
            self.process(row)
        return bool(rows)

    def process(self, row: dict) -> None:
        db = self.ctx.db
        target = db.one("SELECT * FROM targets WHERE id = ?", (row["target_id"],))
        if target is None:
            return
        if not target["enabled"]:
            db.run("UPDATE uploads SET next_try = ? WHERE id = ?", (time.time() + 300, row["id"]))
            return
        local = Path(row["spool_path"] or "")
        if not row["spool_path"] or not local.exists():
            self._fail(row, target, "Local copy is missing", final=True)
            return
        self.current = {"id": row["id"], "path": row["usb_path"], "target": target["name"],
                        "started": time.time()}
        view = self.ctx.target_view(target)
        transport = make_transport(view, self.ctx.secrets.decrypt(target["secret"]), self.ctx.paths)
        try:
            remote = transport.put(local, row["remote_path"])
        except (TransferError, CommandError, OSError) as exc:
            self._fail(row, target, str(exc))
            return
        finally:
            self.current = None
        db.run("UPDATE uploads SET status = 'done', attempts = attempts + 1, finished_at = ?, "
               "last_error = '' WHERE id = ?", (time.time(), row["id"]))
        db.log("info", "upload", f"Uploaded {row['usb_path']} to {target['name']} ({remote})")
        self._finish_event(row["event_id"])

    def _fail(self, row: dict, target: dict, message: str, final: bool = False) -> None:
        attempts = row["attempts"] + 1
        if final or attempts >= MAX_ATTEMPTS:
            self.ctx.db.run(
                "UPDATE uploads SET status = 'failed', attempts = ?, last_error = ?, finished_at = ? WHERE id = ?",
                (attempts, message, time.time(), row["id"]),
            )
            self.ctx.db.log("error", "upload",
                            f"Upload of {row['usb_path']} to {target['name']} failed permanently: {message}")
            self.ctx.notifier.record("upload_failed", row["usb_path"], f"{target['name']}: {message}")
            self._finish_event(row["event_id"])
        else:
            self.ctx.db.run(
                "UPDATE uploads SET attempts = ?, last_error = ?, next_try = ? WHERE id = ?",
                (attempts, message, time.time() + backoff(attempts), row["id"]),
            )
            self.ctx.db.log("warning", "upload",
                            f"Upload of {row['usb_path']} to {target['name']} failed (try {attempts}): {message}")

    def _finish_event(self, event_id: int) -> None:
        db = self.ctx.db
        rows = db.all("SELECT u.status, t.name FROM uploads u JOIN targets t ON t.id = u.target_id "
                      "WHERE u.event_id = ?", (event_id,))
        if any(r["status"] == "pending" for r in rows):
            return
        event = db.one("SELECT * FROM file_events WHERE id = ?", (event_id,))
        if event is None:
            return
        done = [r["name"] for r in rows if r["status"] == "done"]
        if rows and len(done) == len(rows):
            db.run("UPDATE file_index SET uploaded = 1 WHERE path = ? AND size = ? AND mtime = ?",
                   (event["path"], event["size"], event["mtime"]))
            self.ctx.notifier.record("uploaded", event["path"], ", ".join(done))
            self._drop_spool(event)
        # Failed uploads keep their spool copy so they can be retried.

    def _drop_spool(self, event: dict) -> None:
        if not event["spool_path"]:
            return
        spool = Path(event["spool_path"])
        try:
            shutil.rmtree(spool.parent)
        except FileNotFoundError:
            pass
        self.ctx.db.run("UPDATE file_events SET spool_path = '' WHERE id = ?", (event["id"],))

    def retry(self, upload_id: int | None = None) -> int:
        """Reset failed uploads to pending. Returns the number of rows changed."""
        db = self.ctx.db
        if upload_id is None:
            rows = db.all("SELECT u.id FROM uploads u JOIN file_events e ON e.id = u.event_id "
                          "WHERE u.status = 'failed' AND e.spool_path != ''")
        else:
            rows = db.all("SELECT u.id FROM uploads u JOIN file_events e ON e.id = u.event_id "
                          "WHERE u.id = ? AND u.status = 'failed' AND e.spool_path != ''", (upload_id,))
        for r in rows:
            db.run("UPDATE uploads SET status = 'pending', attempts = 0, next_try = 0, last_error = '', "
                   "finished_at = NULL WHERE id = ?", (r["id"],))
        if rows:
            self.wake()
        return len(rows)

    def cleanup_orphans(self) -> int:
        """Remove spool copies that no pending or failed upload needs any more."""
        rows = self.ctx.db.all(
            "SELECT * FROM file_events e WHERE spool_path != '' AND NOT EXISTS "
            "(SELECT 1 FROM uploads u WHERE u.event_id = e.id AND u.status IN ('pending', 'failed'))")
        for event in rows:
            self._drop_spool(event)
        return len(rows)

    def discard(self, upload_id: int) -> bool:
        db = self.ctx.db
        row = db.one("SELECT * FROM uploads WHERE id = ? AND status = 'failed'", (upload_id,))
        if row is None:
            return False
        db.run("UPDATE uploads SET status = 'discarded' WHERE id = ?", (upload_id,))
        remaining = db.scalar("SELECT COUNT(*) FROM uploads WHERE event_id = ? AND status IN ('pending', 'failed')",
                              (row["event_id"],))
        if not remaining:
            event = db.one("SELECT * FROM file_events WHERE id = ?", (row["event_id"],))
            if event:
                self._drop_spool(event)
        return True

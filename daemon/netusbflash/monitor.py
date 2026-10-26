"""Watches the USB image for host writes and picks up new recordings.

The USB host (e.g. a mixing console) writes to the disk image through the
gadget. The Pi must not read the filesystem while the host is writing, so the
monitor waits until the image has not been written for `idle_seconds`. Then:

* sync_mode "detach" (default, safest): the stick is disconnected from the
  host for the duration of the scan, mounted, scanned, new files are copied to
  the spool directory, and the stick is connected again.
* sync_mode "live": the image is mounted read-only while the host stays
  connected. Faster, but the host may change files during the scan.

Uploads then run from the spool directory while the stick is available to the
host again.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import shutil
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .gadget import DEFAULT_USB, GadgetError
from .system import CommandError
from .transports import remote_relative
from .validate import patterns

if TYPE_CHECKING:
    from .service import Context

log = logging.getLogger(__name__)

POLL_SECONDS = 2.0
IGNORED_DIRS = {
    "System Volume Information", "$RECYCLE.BIN", ".Trashes", ".Spotlight-V100",
    ".fseventsd", ".TemporaryItems", "LOST.DIR", ".Trash-1000",
}
IGNORED_FILES = {".DS_Store", "Thumbs.db", "desktop.ini", ".metadata_never_index"}


def is_ignored(name: str) -> bool:
    return name in IGNORED_FILES or name.startswith("._") or name.endswith(".partial")


def matches(path: str, include: str, exclude: str) -> bool:
    name = path.rsplit("/", 1)[-1].lower()
    inc = [p.lower() for p in patterns(include)] or ["*"]
    exc = [p.lower() for p in patterns(exclude)]
    return any(fnmatch.fnmatch(name, p) for p in inc) and not any(fnmatch.fnmatch(name, p) for p in exc)


def walk_files(root: Path) -> dict[str, tuple[int, float]]:
    result: dict[str, tuple[int, float]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS and not d.startswith("._")]
        for name in filenames:
            if is_ignored(name):
                continue
            full = os.path.join(dirpath, name)
            try:
                st = os.stat(full)
            except FileNotFoundError:
                continue
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            result[rel] = (st.st_size, round(st.st_mtime, 3))
    return result


def diff_index(current: dict[str, tuple[int, float]], known: dict[str, dict[str, Any]]):
    created, modified, deleted = [], [], []
    for path, (size, mtime) in current.items():
        row = known.get(path)
        if row is None:
            created.append(path)
        elif row["size"] != size or abs(row["mtime"] - mtime) > 0.001:
            modified.append(path)
    for path in known:
        if path not in current:
            deleted.append(path)
    return sorted(created), sorted(modified), sorted(deleted)


class Monitor(threading.Thread):
    def __init__(self, ctx: "Context"):
        super().__init__(name="monitor", daemon=True)
        self.ctx = ctx
        self.stop_event = threading.Event()
        self.sync_requested = threading.Event()
        self.sync_lock = threading.Lock()
        self.seen_write = ctx.gadget.last_write()
        self.dirty = False
        self.state: dict[str, Any] = {"phase": "idle", "last_error": ""}

    def settings(self) -> dict[str, Any]:
        return self.ctx.db.get_dict_setting("usb", DEFAULT_USB)

    def request_sync(self) -> None:
        self.sync_requested.set()

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.tick()
            except Exception as exc:  # keep the thread alive
                log.exception("monitor tick failed")
                self.state["last_error"] = str(exc)
                self.ctx.db.log("error", "usb", f"Monitor error: {exc}")
                self.stop_event.wait(10)
            self.stop_event.wait(POLL_SECONDS)

    def tick(self) -> None:
        cfg = self.settings()
        gadget = self.ctx.gadget
        if not gadget.image_exists():
            return
        latest = gadget.last_write()
        now = time.time()
        if latest > self.seen_write:
            self.seen_write = latest
            self.dirty = True
            self.state["phase"] = "host_writing"
        idle_for = now - self.seen_write
        manual = self.sync_requested.is_set()
        if manual or (self.dirty and idle_for >= int(cfg["idle_seconds"])):
            self.sync_requested.clear()
            self.sync(cfg, "manual" if manual else "idle")
        elif self.dirty:
            self.state["phase"] = "waiting_idle"
            self.state["idle_for"] = round(idle_for, 1)
        else:
            self.state["phase"] = "idle"

    def sync(self, cfg: dict[str, Any], reason: str) -> dict[str, int]:
        with self.sync_lock:
            gadget = self.ctx.gadget
            detach = cfg["sync_mode"] == "detach"
            writable = detach and bool(cfg["delete_after_upload"])
            was_attached = gadget.state()["attached"]
            self.state["phase"] = "syncing"
            counts = {"created": 0, "modified": 0, "deleted": 0, "cleaned": 0}
            started = time.time()
            try:
                if detach and was_attached:
                    gadget.detach()
                    time.sleep(1.0)  # give the host a moment to notice the removal
                with gadget.mount(writable=writable) as root:
                    if writable:
                        counts["cleaned"] = self.cleanup(root)
                    counts.update(self.scan(root, cfg))
            except (GadgetError, CommandError, OSError) as exc:
                self.state["last_error"] = str(exc)
                self.ctx.db.log("error", "usb", f"Sync failed: {exc}")
                raise
            finally:
                if detach and was_attached:
                    try:
                        gadget.attach()
                    except GadgetError as exc:
                        self.ctx.db.log("error", "usb", f"Could not reconnect the USB stick: {exc}")
                self.seen_write = max(self.seen_write, gadget.last_write())
                self.dirty = False
                self.state["phase"] = "idle"
            summary = {"time": time.time(), "duration": round(time.time() - started, 1),
                       "reason": reason, **counts}
            self.ctx.db.set_setting("last_sync", summary)
            if any(counts.values()):
                self.ctx.db.log(
                    "info", "usb",
                    "Sync ({reason}): {created} new, {modified} changed, {deleted} deleted, "
                    "{cleaned} removed after upload".format(reason=reason, **counts),
                )
            self.state["last_error"] = ""
            return counts

    def cleanup(self, root: Path) -> int:
        """Delete files from the stick whose uploads all succeeded."""
        removed = 0
        for row in self.ctx.db.all("SELECT path, size, mtime FROM file_index WHERE uploaded = 1"):
            full = root / row["path"]
            try:
                st = full.stat()
            except FileNotFoundError:
                self.ctx.db.run("DELETE FROM file_index WHERE path = ?", (row["path"],))
                continue
            if st.st_size != row["size"] or abs(round(st.st_mtime, 3) - row["mtime"]) > 0.001:
                continue  # changed since upload: keep it
            try:
                full.unlink()
            except OSError as exc:
                self.ctx.db.log("warning", "usb", f"Could not delete {row['path']}: {exc}")
                continue
            self.ctx.db.run("DELETE FROM file_index WHERE path = ?", (row["path"],))
            removed += 1
        return removed

    def scan(self, root: Path, cfg: dict[str, Any]) -> dict[str, int]:
        db = self.ctx.db
        current = walk_files(root)
        known = {row["path"]: row for row in db.all("SELECT * FROM file_index")}
        created, modified, deleted = diff_index(current, known)
        now = time.time()
        baseline = not db.get_setting("index_initialized", False)

        with db.transaction() as conn:
            for path in created:
                size, mtime = current[path]
                conn.execute(
                    "INSERT INTO file_index(path, size, mtime, first_seen, last_seen) VALUES(?, ?, ?, ?, ?)",
                    (path, size, mtime, now, now),
                )
            for path in modified:
                size, mtime = current[path]
                conn.execute(
                    "UPDATE file_index SET size = ?, mtime = ?, last_seen = ?, uploaded = 0 WHERE path = ?",
                    (size, mtime, now, path),
                )
            for path in deleted:
                conn.execute("DELETE FROM file_index WHERE path = ?", (path,))

        if baseline:
            db.set_setting("index_initialized", True)
            db.log("info", "usb", f"Initial scan recorded {len(current)} existing files (no uploads, no emails)")
            return {"created": 0, "modified": 0, "deleted": 0}

        targets = db.all("SELECT * FROM targets WHERE enabled = 1")
        for path in created + modified:
            kind = "created" if path in created else "modified"
            self._handle_file(root, path, current[path], kind, cfg, targets)
        for path in deleted:
            db.run("INSERT INTO file_events(time, path, event) VALUES(?, ?, 'deleted')", (time.time(), path))
            self.ctx.notifier.record("deleted", path)
        return {"created": len(created), "modified": len(modified), "deleted": len(deleted)}

    def _handle_file(self, root: Path, path: str, stat: tuple[int, float], kind: str,
                     cfg: dict[str, Any], targets: list[dict[str, Any]]) -> None:
        db = self.ctx.db
        size, mtime = stat
        event_id = db.run(
            "INSERT INTO file_events(time, path, event, size, mtime) VALUES(?, ?, ?, ?, ?)",
            (time.time(), path, kind, size, mtime),
        )
        self.ctx.notifier.record(kind, path)
        if not targets or not matches(path, cfg["include"], cfg["exclude"]):
            return
        spool_dir = self.ctx.paths.spool / str(event_id)
        spool_dir.mkdir(parents=True, exist_ok=True)
        spool_file = spool_dir / path.rsplit("/", 1)[-1]
        free = shutil.disk_usage(self.ctx.paths.spool).free
        if free - size < 256 * 1024 * 1024:
            db.log("error", "usb", f"Not enough free space to queue {path} for upload")
            return
        shutil.copy2(root / path, spool_file)
        hostname = self.ctx.hostname()
        now = time.time()
        with db.transaction() as conn:
            conn.execute("UPDATE file_events SET spool_path = ? WHERE id = ?", (str(spool_file), event_id))
            for target in targets:
                target_view = self.ctx.target_view(target)
                rel = remote_relative(target_view, path, now, hostname)
                conn.execute(
                    "INSERT INTO uploads(event_id, target_id, remote_path, created_at) VALUES(?, ?, ?, ?)",
                    (event_id, target["id"], rel, now),
                )
        self.ctx.uploader.wake()

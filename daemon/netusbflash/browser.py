"""Makes the USB stick's files available to the file manager (FileGator).

Modes:

* "off":  nothing is mounted for the file manager.
* "view": the image is mounted read-only. The USB host stays connected, so
          the view can lag behind what the host writes; "refresh" remounts.
* "edit": the stick is disconnected from the host and mounted read/write,
          so files can be deleted, renamed or uploaded. Edit mode ends by
          itself after `edit_timeout_minutes` so a forgotten session never
          leaves the mixing console without its stick.

The monitor pauses the file manager mount while it scans the stick and does
not scan at all while edit mode is active.
"""

from __future__ import annotations

import grp
import logging
import threading
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

from .config import SOCKET_GROUP
from .gadget import GadgetError
from .system import CommandError

if TYPE_CHECKING:
    from .service import Context

log = logging.getLogger(__name__)

MODES = ("off", "view", "edit")
DEFAULT_BROWSER: dict[str, Any] = {"edit_timeout_minutes": 30}


class BrowserError(Exception):
    pass


class FileBrowser(threading.Thread):
    def __init__(self, ctx: "Context"):
        super().__init__(name="browser", daemon=True)
        self.ctx = ctx
        self.lock = threading.RLock()
        self.mode = "off"
        self.since = 0.0
        self.edit_until = 0.0
        self.host_was_attached = False
        self.stop_event = threading.Event()

    # Helpers ---------------------------------------------------------------

    @property
    def path(self):
        return self.ctx.paths.sim_dir if self.ctx.simulated else self.ctx.paths.browse_dir

    @staticmethod
    def _gid() -> int | None:
        try:
            return grp.getgrnam(SOCKET_GROUP).gr_gid
        except KeyError:
            return None

    def settings(self) -> dict[str, Any]:
        return self.ctx.db.get_dict_setting("browser", DEFAULT_BROWSER)

    def state(self) -> dict[str, Any]:
        with self.lock:
            return {
                "mode": self.mode,
                "since": self.since or None,
                "edit_until": self.edit_until or None,
                "path": str(self.path),
                "image_exists": self.ctx.gadget.image_exists(),
                "timeout_minutes": self.settings()["edit_timeout_minutes"],
            }

    def _mount(self, writable: bool) -> None:
        gadget = self.ctx.gadget
        if gadget.is_mounted(self.path) and not self.ctx.simulated:
            gadget.unmount_at(self.path)
        gadget.mount_at(self.path, writable, self._gid())

    def _unmount(self, writable: bool = False) -> None:
        if self.ctx.simulated:
            return
        if self.ctx.gadget.is_mounted(self.path):
            self.ctx.gadget.unmount_at(self.path, writable)

    # Mode changes ------------------------------------------------------------

    def set_mode(self, mode: str, user: dict | None = None) -> dict[str, Any]:
        if mode not in MODES:
            raise BrowserError("invalid mode")
        if mode != "off" and not self.ctx.gadget.image_exists():
            raise BrowserError("No USB image yet.")
        # The monitor must not scan while we switch.
        with self.ctx.monitor.sync_lock, self.lock:
            if mode == self.mode and mode != "view":
                return self.state()
            try:
                self._leave_current()
                if mode == "view":
                    self._mount(writable=False)
                elif mode == "edit":
                    state = self.ctx.gadget.state()
                    self.host_was_attached = bool(state.get("attached"))
                    if self.host_was_attached:
                        self.ctx.gadget.detach()
                        time.sleep(1.0)
                    self._mount(writable=True)
                    self.edit_until = time.time() + int(self.settings()["edit_timeout_minutes"]) * 60
                self.mode = mode
                self.since = time.time() if mode != "off" else 0.0
            except (GadgetError, CommandError, OSError) as exc:
                self.mode = "off"
                self._reattach()
                raise BrowserError(str(exc)) from exc
        what = {"off": "closed", "view": "opened read-only", "edit": "opened for editing (stick disconnected)"}[mode]
        self.ctx.db.log("info", "files", f"File manager {what}")
        if user is not None:
            self.ctx.db.audit(user, f"files.{mode}")
        if mode != "edit":
            # Files may have changed in edit mode: let the monitor pick them up.
            self.ctx.monitor.request_sync()
        return self.state()

    def _leave_current(self) -> None:
        if self.mode == "view":
            self._unmount()
        elif self.mode == "edit":
            self._unmount(writable=True)
            self._reattach()
        self.mode = "off"
        self.edit_until = 0.0

    def _reattach(self) -> None:
        if self.host_was_attached:
            self.host_was_attached = False
            try:
                self.ctx.gadget.attach()
            except (GadgetError, OSError) as exc:
                self.ctx.db.log("error", "files", f"Could not reconnect the USB stick: {exc}")

    def refresh(self) -> dict[str, Any]:
        with self.lock:
            if self.mode == "view":
                self._mount(writable=False)
            elif self.mode == "edit":
                self.edit_until = time.time() + int(self.settings()["edit_timeout_minutes"]) * 60
        return self.state()

    def is_editing(self) -> bool:
        return self.mode == "edit"

    @contextmanager
    def paused(self) -> Iterator[None]:
        """Unmount a read-only view while the monitor works on the image."""
        with self.lock:
            was_view = self.mode == "view"
            if was_view:
                self._unmount()
            try:
                yield
            finally:
                if was_view:
                    try:
                        self._mount(writable=False)
                    except (GadgetError, CommandError, OSError) as exc:
                        self.mode = "off"
                        self.ctx.db.log("warning", "files", f"File manager view could not be remounted: {exc}")

    def shutdown(self) -> None:
        with self.lock:
            try:
                self._leave_current()
            except (GadgetError, CommandError, OSError):
                log.exception("file browser shutdown failed")

    # Worker: end edit mode after the timeout -------------------------------

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        while not self.stop_event.wait(5):
            if self.mode == "edit" and self.edit_until and time.time() > self.edit_until:
                self.ctx.db.log("warning", "files", "Edit mode timed out; the USB stick is connected again")
                try:
                    self.set_mode("view")
                except BrowserError as exc:
                    self.ctx.db.log("error", "files", f"Leaving edit mode failed: {exc}")

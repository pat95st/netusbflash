"""Service entry point: wires all components and serves the API."""

from __future__ import annotations

import argparse
import json
import logging
import signal
import threading
import time
from typing import Any, Callable

from . import __version__, system
from .api import Router, make_server
from .auth import AuthService
from .backup import BackupService
from .browser import FileBrowser
from .config import Paths, load_paths, simulate
from .converter import Converter
from .crypto import SecretBox
from .db import Database
from .gadget import DEFAULT_USB, GadgetBackend, GadgetError, make_gadget
from .handlers import register
from .mailer import Mailer, Notifier
from .monitor import Monitor
from .setup import SetupState
from .system import CommandError
from .cloud import dump_secret, load_secret
from .transports import DEFAULT_OPTIONS, Transport, make_transport
from .updater import Updater
from .uploader import Uploader

log = logging.getLogger("netusbflash")


class Context:
    """Holds every long-lived component; passed to handlers and workers."""

    def __init__(self, paths: Paths, simulated: bool):
        self.paths = paths
        self.simulated = simulated
        paths.ensure()
        self.db = Database(paths.db)
        self.db.migrate()
        self.secrets = SecretBox(paths.secret_key)
        self.auth = AuthService(self.db)
        self.setup = SetupState(self.db, paths)
        self.gadget: GadgetBackend = make_gadget(paths, simulated)
        self.notifier = Notifier(self)
        self.mailer = Mailer(self)
        self.uploader = Uploader(self)
        self.converter = Converter(self)
        self.monitor = Monitor(self)
        self.browser = FileBrowser(self)
        self.updater = Updater(self)
        self.backup = BackupService(self)

    @property
    def workers(self) -> tuple:
        return (self.monitor, self.converter, self.uploader, self.mailer, self.browser, self.updater, self.backup)

    def usb_settings(self) -> dict[str, Any]:
        return self.db.get_dict_setting("usb", DEFAULT_USB)

    def hostname(self) -> str:
        if self.simulated:
            stored = self.db.get_setting("system", {}) or {}
            return stored.get("hostname") or system.hostname()
        return system.hostname()

    @staticmethod
    def target_view(row: dict[str, Any]) -> dict[str, Any]:
        """Target row with options decoded and defaults applied."""
        options = row.get("options") or {}
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except json.JSONDecodeError:
                options = {}
        return {**row, "options": {**DEFAULT_OPTIONS, **options}}

    def target_secret(self, target_id: int) -> str:
        """Decrypted secret of a saved target ('' if it does not exist)."""
        secret = self.db.scalar("SELECT secret FROM targets WHERE id = ?", (target_id,))
        return self.secrets.decrypt(secret) if secret else ""

    def persist_target_secret(self, target_id: int, protocol: str, changes: dict[str, str]) -> None:
        """Merge values refreshed by rclone (tokens, cookies) into a saved target."""
        with self.db.write_lock:
            row = self.db.one("SELECT protocol, secret FROM targets WHERE id = ?", (target_id,))
            if row is None or row["protocol"] != protocol:
                return
            data = load_secret(protocol, self.secrets.decrypt(row["secret"]))
            data.update(changes)
            self.db.run("UPDATE targets SET secret = ? WHERE id = ?",
                        (self.secrets.encrypt(dump_secret(protocol, data)), target_id))

    def transport_for(self, target: dict[str, Any]) -> Transport:
        """Transport for a saved target that keeps refreshed tokens."""
        target_id, protocol = target["id"], target["protocol"]
        return make_transport(
            self.target_view(target), self.secrets.decrypt(target["secret"]), self.paths,
            on_secret=lambda changes: self.persist_target_secret(target_id, protocol, changes),
            reload=lambda: self.target_secret(target_id))

    def defer(self, func: Callable[[], None], delay: float = 1.0) -> None:
        """Run func shortly after the current API response was sent."""
        def runner() -> None:
            time.sleep(delay)
            try:
                func()
            except CommandError as exc:
                self.db.log("error", "system", str(exc))
        threading.Thread(target=runner, daemon=True).start()


def housekeeping(ctx: Context, stop: threading.Event) -> None:
    while not stop.wait(3600):
        try:
            ctx.auth.prune_sessions()
            ctx.db.prune()
            ctx.uploader.cleanup_orphans()
        except Exception:
            log.exception("housekeeping failed")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="netusbflash", description="NetUSBFlash service")
    parser.add_argument("--simulate", action="store_true", help="simulate the USB gadget with a directory")
    parser.add_argument("--debug", action="store_true", help="verbose logging")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    paths = load_paths()
    ctx = Context(paths, simulated=args.simulate or simulate())
    ctx.setup.ensure_code()
    ctx.db.log("info", "system", f"Service started (version {__version__}"
                                 f"{', simulated USB' if ctx.simulated else ''})")

    cfg = ctx.usb_settings()
    if cfg["enabled"] and ctx.gadget.image_exists() and ctx.setup.completed():
        try:
            ctx.gadget.apply(cfg)
            ctx.db.log("info", "usb", "USB stick connected to the host port")
        except (GadgetError, OSError, CommandError) as exc:
            ctx.db.log("error", "usb", f"Could not start the USB gadget: {exc}")

    router = Router()
    register(router, ctx)
    server = make_server(ctx, router, paths.socket)

    stop = threading.Event()
    for worker in ctx.workers:
        worker.start()
    threading.Thread(target=housekeeping, args=(ctx, stop), name="housekeeping", daemon=True).start()

    def shutdown(signum: int, frame: Any) -> None:
        log.info("stopping (signal %s)", signum)
        stop.set()
        for worker in ctx.workers:
            worker.stop()
        ctx.browser.shutdown()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    log.info("listening on %s", paths.socket)
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
        paths.socket.unlink(missing_ok=True)
        log.info("stopped")

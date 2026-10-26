"""First-run setup wizard state and the one-time setup code."""

from __future__ import annotations

import hmac
import os
import secrets
import threading
import time

from .config import Paths
from .db import Database

STEPS = ("admin", "system", "usb", "target", "smtp", "finish")
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_MAX_ATTEMPTS_PER_MINUTE = 5


def generate_code() -> str:
    raw = "".join(secrets.choice(_ALPHABET) for _ in range(12))
    return "-".join(raw[i:i + 4] for i in range(0, 12, 4))


def normalise_code(code: str) -> str:
    cleaned = "".join(ch for ch in (code or "").upper() if ch in _ALPHABET)
    return "-".join(cleaned[i:i + 4] for i in range(0, len(cleaned), 4))


class SetupState:
    def __init__(self, db: Database, paths: Paths):
        self.db = db
        self.paths = paths
        self._attempts: list[float] = []
        self._lock = threading.Lock()

    def completed(self) -> bool:
        return bool(self.db.get_setting("setup_completed", False))

    def step(self) -> str:
        step = self.db.get_setting("setup_step", STEPS[0])
        return step if step in STEPS else STEPS[0]

    def set_step(self, step: str) -> None:
        if step in STEPS:
            self.db.set_setting("setup_step", step)

    def advance(self, finished_step: str) -> str:
        """Move past finished_step if it is the current or an earlier step."""
        current = STEPS.index(self.step())
        done = STEPS.index(finished_step)
        nxt = STEPS[min(done + 1, len(STEPS) - 1)]
        if done >= current:
            self.set_step(nxt)
        return self.step()

    def ensure_code(self) -> None:
        if self.completed() or self.paths.setup_token.exists():
            return
        self.paths.setup_token.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.paths.setup_token, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(generate_code() + "\n")

    def read_code(self) -> str:
        try:
            return self.paths.setup_token.read_text().strip()
        except FileNotFoundError:
            return ""

    def check(self, code: str | None) -> bool:
        """Validate a setup code with simple rate limiting."""
        if self.completed():
            return False
        now = time.time()
        with self._lock:
            self._attempts = [t for t in self._attempts if now - t < 60]
            if len(self._attempts) >= _MAX_ATTEMPTS_PER_MINUTE:
                return False
            expected = self.read_code()
            ok = bool(expected) and hmac.compare_digest(normalise_code(code or ""), expected)
            if not ok:
                self._attempts.append(now)
            return ok

    def finish(self) -> None:
        self.db.set_setting("setup_completed", True)
        self.db.set_setting("setup_step", STEPS[0])
        try:
            self.paths.setup_token.unlink()
        except FileNotFoundError:
            pass

    def reset(self, wipe_users: bool = False) -> None:
        self.db.set_setting("setup_completed", False)
        self.db.set_setting("setup_step", STEPS[0])
        if wipe_users:
            self.db.run("DELETE FROM users")
        try:
            self.paths.setup_token.unlink()
        except FileNotFoundError:
            pass
        self.ensure_code()

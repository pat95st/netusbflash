"""Users, password hashing, sessions and roles."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from typing import Any

from .db import Database

ROLES: dict[str, int] = {"viewer": 1, "operator": 2, "manager": 3, "admin": 4}
LOCALES = ("en", "de")

SESSION_IDLE_SECONDS = 30 * 60
SESSION_MAX_SECONDS = 12 * 3600
MAX_FAILED_LOGINS = 5
LOCK_SECONDS = 15 * 60

# scrypt parameters: about 16 MiB of memory per hash, fine on a Pi Zero 2 W.
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


class AuthError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R,
                            p=_SCRYPT_P, dklen=32)
    return "scrypt${}${}${}${}${}".format(
        _SCRYPT_N, _SCRYPT_R, _SCRYPT_P,
        base64.b64encode(salt).decode(), base64.b64encode(digest).decode(),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, hash_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(hash_b64)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=base64.b64decode(salt_b64),
                                n=int(n), r=int(r), p=int(p), dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


def generate_password(length: int = 16) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def public_user(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "role": row["role"],
        "locale": row["locale"],
        "must_change_pw": bool(row["must_change_pw"]),
        "locked": row["locked_until"] > time.time(),
        "disabled": bool(row["disabled"]),
        "created_at": row["created_at"],
        "last_login": row["last_login"],
    }


def has_role(user: dict[str, Any] | None, role: str) -> bool:
    return user is not None and ROLES.get(user["role"], 0) >= ROLES[role]


class AuthService:
    def __init__(self, db: Database):
        self.db = db

    def create_user(self, username: str, email: str, role: str, locale: str, password: str,
                    must_change_pw: bool = False) -> int:
        if role not in ROLES:
            raise ValueError("unknown role")
        return self.db.run(
            "INSERT INTO users(username, email, role, locale, password_hash, must_change_pw, created_at) "
            "VALUES(?, ?, ?, ?, ?, ?, ?)",
            (username, email, role, locale if locale in LOCALES else "en",
             hash_password(password), int(must_change_pw), time.time()),
        )

    def get_user(self, user_id: int) -> dict[str, Any] | None:
        return self.db.one("SELECT * FROM users WHERE id = ?", (user_id,))

    def find_user(self, username: str) -> dict[str, Any] | None:
        return self.db.one("SELECT * FROM users WHERE username = ?", (username,))

    def set_password(self, user_id: int, password: str, must_change: bool = False) -> None:
        self.db.run(
            "UPDATE users SET password_hash = ?, must_change_pw = ?, failed_logins = 0, "
            "locked_until = 0 WHERE id = ?",
            (hash_password(password), int(must_change), user_id),
        )
        # Invalidate other sessions of this user.
        self.db.run("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def login(self, username: str, password: str) -> tuple[str, dict[str, Any]]:
        now = time.time()
        user = self.find_user(username)
        if user is None:
            # Spend comparable time to make user enumeration harder.
            verify_password(password, hash_password("dummy-password"))
            raise AuthError("auth_failed")
        if user["disabled"]:
            raise AuthError("auth_failed")
        if user["locked_until"] > now:
            raise AuthError("locked")
        if not verify_password(password, user["password_hash"]):
            failed = user["failed_logins"] + 1
            locked_until = now + LOCK_SECONDS if failed >= MAX_FAILED_LOGINS else 0
            self.db.run(
                "UPDATE users SET failed_logins = ?, locked_until = ? WHERE id = ?",
                (0 if locked_until else failed, locked_until, user["id"]),
            )
            if locked_until:
                self.db.log("warning", "auth", f"User {user['username']} locked after {failed} failed logins")
                raise AuthError("locked")
            raise AuthError("auth_failed")
        token = secrets.token_urlsafe(32)
        self.db.run("UPDATE users SET failed_logins = 0, locked_until = 0, last_login = ? WHERE id = ?",
                    (now, user["id"]))
        self.db.run("INSERT INTO sessions(token_hash, user_id, created_at, last_seen) VALUES(?, ?, ?, ?)",
                    (_token_hash(token), user["id"], now, now))
        return token, self.get_user(user["id"]) or user

    def session_user(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        now = time.time()
        session = self.db.one("SELECT * FROM sessions WHERE token_hash = ?", (_token_hash(token),))
        if session is None:
            return None
        if now - session["last_seen"] > SESSION_IDLE_SECONDS or now - session["created_at"] > SESSION_MAX_SECONDS:
            self.db.run("DELETE FROM sessions WHERE token_hash = ?", (session["token_hash"],))
            return None
        user = self.get_user(session["user_id"])
        if user is None or user["disabled"]:
            return None
        self.db.run("UPDATE sessions SET last_seen = ? WHERE token_hash = ?", (now, session["token_hash"]))
        return user

    def logout(self, token: str | None) -> None:
        if token:
            self.db.run("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))

    def prune_sessions(self) -> None:
        now = time.time()
        self.db.run("DELETE FROM sessions WHERE last_seen < ? OR created_at < ?",
                    (now - SESSION_IDLE_SECONDS, now - SESSION_MAX_SECONDS))

    def active_admins(self) -> int:
        return int(self.db.scalar("SELECT COUNT(*) FROM users WHERE role = 'admin' AND disabled = 0") or 0)

"""Input validation helpers shared by the API handlers."""

from __future__ import annotations

import re
from typing import Any

USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,253}\.[^@\s]{2,63}$")
HOSTNAME_RE = re.compile(r"^(?=.{1,63}$)[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?$")
HOST_RE = re.compile(r"^[A-Za-z0-9.:\[\]-]{1,253}$")
TIMEZONE_RE = re.compile(r"^[A-Za-z_]+(/[A-Za-z0-9_+-]+){0,2}$|^UTC$")
LABEL_RE = re.compile(r"^[A-Z0-9_ -]{1,11}$")
HEX16_RE = re.compile(r"^0x[0-9a-fA-F]{4}$")
SAFE_TEXT_RE = re.compile(r"^[\x20-\x7e]{0,64}$")
BWLIMIT_RE = re.compile(r"^$|^\d{1,6}[KMG]?$")

PASSWORD_MIN_LENGTH = 12


class ValidationError(Exception):
    def __init__(self, fields: dict[str, str]):
        super().__init__("validation failed")
        self.fields = fields


class Validator:
    """Collects field errors; call raise_if_errors() at the end."""

    def __init__(self, data: dict[str, Any] | None):
        self.data = data or {}
        self.errors: dict[str, str] = {}
        self.clean: dict[str, Any] = {}

    def _get(self, name: str, default: Any = None) -> Any:
        return self.data.get(name, default)

    def string(self, name: str, *, required: bool = False, max_len: int = 255,
               pattern: re.Pattern[str] | None = None, default: str = "") -> str:
        value = self._get(name, default)
        if value is None:
            value = ""
        if not isinstance(value, str):
            self.errors[name] = "invalid"
            return default
        if "\x00" in value or "\n" in value or "\r" in value:
            self.errors[name] = "invalid"
            return default
        value = value.strip()
        if required and not value:
            self.errors[name] = "required"
        elif len(value) > max_len:
            self.errors[name] = "too_long"
        elif value and pattern is not None and not pattern.match(value):
            self.errors[name] = "invalid"
        self.clean[name] = value
        return value

    def integer(self, name: str, *, minimum: int, maximum: int, default: int | None = None,
                required: bool = False) -> int | None:
        value = self._get(name, default)
        if value in (None, ""):
            if required:
                self.errors[name] = "required"
            self.clean[name] = default
            return default
        try:
            number = int(value)
        except (TypeError, ValueError):
            self.errors[name] = "invalid"
            return default
        if number < minimum or number > maximum:
            self.errors[name] = "out_of_range"
        self.clean[name] = number
        return number

    def boolean(self, name: str, default: bool = False) -> bool:
        value = self._get(name, default)
        if isinstance(value, bool):
            result = value
        elif isinstance(value, (int, float)):
            result = bool(value)
        elif isinstance(value, str):
            result = value.lower() in ("1", "true", "yes", "on")
        else:
            result = default
        self.clean[name] = result
        return result

    def choice(self, name: str, choices: tuple[str, ...] | list[str], default: str | None = None) -> str:
        value = self._get(name, default)
        if value not in choices:
            self.errors[name] = "invalid"
            return default or choices[0]
        self.clean[name] = value
        return value

    def email(self, name: str, *, required: bool = False) -> str:
        return self.string(name, required=required, max_len=254, pattern=EMAIL_RE)

    def emails(self, name: str, *, required: bool = False) -> list[str]:
        raw = self._get(name, "")
        if isinstance(raw, list):
            items = [str(x).strip() for x in raw]
        else:
            items = [x.strip() for x in str(raw or "").replace(";", ",").split(",")]
        items = [x for x in items if x]
        if required and not items:
            self.errors[name] = "required"
        elif any(not EMAIL_RE.match(x) for x in items) or len(items) > 20:
            self.errors[name] = "invalid"
        self.clean[name] = items
        return items

    def password(self, name: str, *, required: bool = True) -> str:
        value = self._get(name, "")
        if not isinstance(value, str):
            self.errors[name] = "invalid"
            return ""
        if not value:
            if required:
                self.errors[name] = "required"
        elif len(value) < PASSWORD_MIN_LENGTH:
            self.errors[name] = "too_short"
        elif len(value) > 256:
            self.errors[name] = "too_long"
        self.clean[name] = value
        return value

    def remote_path(self, name: str) -> str:
        value = self.string(name, max_len=512)
        if any(part == ".." for part in value.replace("\\", "/").split("/")):
            self.errors[name] = "invalid"
        return value

    def raise_if_errors(self) -> None:
        if self.errors:
            raise ValidationError(self.errors)


def patterns(raw: str) -> list[str]:
    return [p.strip() for p in (raw or "").split(",") if p.strip()]

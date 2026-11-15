"""Cloud storage providers: Dropbox, iCloud Drive, OneDrive, Google Drive, Box.

All of them are served by rclone. The OAuth providers (Dropbox, OneDrive,
Google Drive, Box) need a token that the user creates on a computer with a web
browser with ``rclone authorize "<backend>"`` and pastes into the web
interface, because the Pi has no browser. iCloud Drive logs in with the Apple
ID, the password and a two-factor code.

For these protocols the encrypted ``secret`` column of a target holds a small
JSON object instead of a plain password, for example
``{"token": "{...}", "client_secret": "..."}`` or
``{"password": "...", "trust_token": "...", "cookies": "..."}``.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
import urllib.error
import urllib.request
from typing import Any

OAUTH_PROTOCOLS = ("dropbox", "onedrive", "gdrive", "box")
CLOUD_PROTOCOLS = (*OAUTH_PROTOCOLS, "icloud")

# rclone backend name for each protocol.
RCLONE_BACKENDS = {
    "dropbox": "dropbox",
    "onedrive": "onedrive",
    "gdrive": "drive",
    "box": "box",
    "icloud": "iclouddrive",
}

# Keys of the secret object per protocol.
SECRET_KEYS = {
    "dropbox": ("token", "client_secret"),
    "onedrive": ("token", "client_secret"),
    "gdrive": ("token", "client_secret"),
    "box": ("token", "client_secret"),
    "icloud": ("password", "trust_token", "cookies"),
}

# Values rclone may change in its config file during a run (refreshed OAuth
# tokens, renewed iCloud session cookies). They are written back to the
# database, otherwise the target stops working once the original token expires.
WRITEBACK_KEYS = {
    "dropbox": ("token",),
    "onedrive": ("token",),
    "gdrive": ("token",),
    "box": ("token",),
    "icloud": ("trust_token", "cookies"),
}

ONEDRIVE_DRIVE_TYPES = ("personal", "business", "documentLibrary")
ONEDRIVE_DRIVE_URL = "https://graph.microsoft.com/v1.0/me/drive"
MAX_TOKEN_LENGTH = 16384

_PASTE_BLOCK = re.compile(r"--->(.*?)<---", re.S)


class CloudError(Exception):
    pass


def is_cloud(protocol: str) -> bool:
    return protocol in CLOUD_PROTOCOLS


def load_secret(protocol: str, plain: str) -> dict[str, str]:
    """Decode the decrypted secret of a target into a dict."""
    plain = plain or ""
    if protocol not in CLOUD_PROTOCOLS:
        return {"password": plain} if plain else {}
    if not plain:
        return {}
    try:
        data = json.loads(plain)
    except json.JSONDecodeError:
        data = None
    if not isinstance(data, dict):
        # A plain password, e.g. after switching a target from SMB to iCloud.
        return {"password": plain}
    return {k: v for k, v in data.items() if k in SECRET_KEYS[protocol] and isinstance(v, str) and v}


def dump_secret(protocol: str, data: dict[str, str]) -> str:
    """Encode a secret dict for storage (before encryption)."""
    if protocol not in CLOUD_PROTOCOLS:
        return data.get("password", "")
    clean = {k: data[k] for k in SECRET_KEYS[protocol] if data.get(k)}
    return json.dumps(clean, sort_keys=True, separators=(",", ":")) if clean else ""


def _token_object(value: Any) -> dict[str, Any] | None:
    """Find the OAuth token in a decoded paste (raw token or rclone wrapper)."""
    if isinstance(value, dict):
        if "access_token" in value or "refresh_token" in value:
            return value
        inner = value.get("token")
        if isinstance(inner, str):
            try:
                return _token_object(json.loads(inner))
            except json.JSONDecodeError:
                return None
        return _token_object(inner) if isinstance(inner, dict) else None
    return None


def _decode_base64(text: str) -> Any:
    compact = re.sub(r"\s+", "", text)
    padded = compact + "=" * (-len(compact) % 4)
    for decoder in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            return json.loads(decoder(padded).decode("utf-8"))
        except (binascii.Error, ValueError, UnicodeDecodeError):
            continue
    return None


def normalize_token(raw: str) -> str:
    """Accept what ``rclone authorize`` prints and return the token as compact JSON.

    Accepted: the raw token JSON, the base64 blob newer rclone versions print,
    or the whole output including the "Paste the following ... <---End paste"
    lines. Raises CloudError if no usable token is found.
    """
    text = (raw or "").strip()
    if not text:
        raise CloudError("empty")
    if len(text) > MAX_TOKEN_LENGTH:
        raise CloudError("too_long")
    match = _PASTE_BLOCK.search(text)
    if match:
        text = match.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    decoded: Any = None
    if start != -1 and end > start:
        try:
            decoded = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            decoded = None
    if decoded is None:
        decoded = _decode_base64(text)
    token = _token_object(decoded)
    if not token:
        raise CloudError("invalid")
    allowed = {k: v for k, v in token.items()
               if k in ("access_token", "token_type", "refresh_token", "expiry", "expires_in")}
    if not allowed.get("access_token") and not allowed.get("refresh_token"):
        raise CloudError("invalid")
    return json.dumps(allowed, separators=(",", ":"))


def detect_onedrive_drive(token_json: str, timeout: float = 20) -> tuple[str, str]:
    """Return (drive_id, drive_type) of the user's default OneDrive.

    rclone needs both values but ``rclone authorize`` only returns the token,
    so they are looked up with the Microsoft Graph API right after the token
    was pasted (the access token is valid for about an hour).
    """
    try:
        access = json.loads(token_json).get("access_token", "")
    except (json.JSONDecodeError, AttributeError):
        access = ""
    if not access:
        raise CloudError("The token contains no access token.")
    request = urllib.request.Request(ONEDRIVE_DRIVE_URL, headers={
        "Authorization": f"Bearer {access}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:  # noqa: S310 - fixed https URL
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise CloudError(f"Microsoft Graph answered HTTP {exc.code}") from exc
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise CloudError(f"Microsoft Graph is not reachable: {exc}") from exc
    drive_id = str(data.get("id") or "")
    drive_type = str(data.get("driveType") or "")
    if not drive_id or drive_type not in ONEDRIVE_DRIVE_TYPES:
        raise CloudError("Microsoft Graph returned no usable drive.")
    return drive_id, drive_type


def read_rclone_section(text: str, section: str) -> dict[str, str]:
    """Parse one section of an rclone config file."""
    values: dict[str, str] = {}
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1]
        elif current == section and "=" in stripped and not stripped.startswith(("#", ";")):
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def parse_config_answer(output: str) -> dict[str, Any]:
    """Parse the JSON that ``rclone config ... --non-interactive`` prints."""
    end = output.rfind("}")
    while end != -1:
        start = output.rfind("{", 0, end)
        while start != -1:
            try:
                data = json.loads(output[start:end + 1])
            except json.JSONDecodeError:
                start = output.rfind("{", 0, start)
                continue
            if isinstance(data, dict) and "State" in data:
                return data
            start = output.rfind("{", 0, start)
        end = output.rfind("}", 0, end)
    raise CloudError("Unexpected answer from rclone: " + (output.strip().splitlines() or [""])[-1][-300:])

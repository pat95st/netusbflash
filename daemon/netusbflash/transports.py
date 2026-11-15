"""Upload transports for each supported protocol.

rclone handles SMB/CIFS, WebDAV (incl. Nextcloud), FTP, FTPS, SFTP and the
cloud services Dropbox, iCloud Drive, OneDrive, Google Drive and Box.
SSHFS targets are served by rclone's SFTP backend, because SSHFS is SFTP on
the wire. SCP uses the OpenSSH client. "local" copies into a local directory
(useful for USB disks attached to the Pi and for tests).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable

from .cloud import (CLOUD_PROTOCOLS, RCLONE_BACKENDS, WRITEBACK_KEYS, CloudError, load_secret,
                    parse_config_answer, read_rclone_section)
from .config import Paths
from .system import CommandError, run, which

PROTOCOLS = ("smb", "webdav", "ftp", "ftps", "sftp", "sshfs", "scp",
             "dropbox", "icloud", "onedrive", "gdrive", "box", "local")
DEFAULT_PORTS = {"smb": 445, "ftp": 21, "ftps": 21, "sftp": 22, "sshfs": 22, "scp": 22}

DEFAULT_OPTIONS: dict[str, Any] = {
    "domain": "",              # smb
    "vendor": "other",         # webdav: other | nextcloud | owncloud
    "tls_mode": "explicit",    # ftps: explicit | implicit
    "insecure_tls": False,     # skip certificate verification (ftps/webdav)
    "auth": "password",        # sftp/sshfs/scp: password | key
    "subfolder": "{date}",     # template below the target path
    "keep_structure": True,    # keep folder structure from the USB stick
    "bwlimit": "",             # rclone bandwidth limit, e.g. 5M
    "client_id": "",           # dropbox/onedrive/gdrive/box: own OAuth app (optional)
    "root_folder_id": "",      # gdrive: start folder ID (optional)
    "team_drive": "",          # gdrive: shared drive ID (optional)
    "drive_id": "",            # onedrive: detected when the token is pasted
    "drive_type": "",          # onedrive: personal | business | documentLibrary
}

# rclone 1.69 added iCloud Drive; older versions report an unknown backend.
ICLOUD_MIN_RCLONE = "1.69"

# One lock per target, so that two rclone runs never refresh the same OAuth
# token at the same time (Box refresh tokens can be used only once).
_locks: dict[Any, threading.Lock] = {}
_locks_guard = threading.Lock()


def _target_lock(key: Any) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())

_SCP_SAFE = re.compile(r"[^A-Za-z0-9._/-]")


class TransferError(Exception):
    pass


def render_subfolder(template: str, when: float, hostname: str) -> str:
    lt = time.localtime(when)
    values = {
        "date": time.strftime("%Y-%m-%d", lt),
        "year": time.strftime("%Y", lt),
        "month": time.strftime("%m", lt),
        "day": time.strftime("%d", lt),
        "time": time.strftime("%H-%M-%S", lt),
        "hostname": hostname,
    }
    result = template or ""
    for key, value in values.items():
        result = result.replace("{" + key + "}", value)
    return result.strip("/")


def join_remote(*parts: str) -> str:
    """Join path parts with '/', keeping a leading '/' of the first part."""
    cleaned = [p for p in parts if p and p.strip("/")]
    if not cleaned:
        return parts[0] if parts and parts[0].startswith("/") else ""
    lead = "/" if cleaned[0].startswith("/") else ""
    return lead + "/".join(p.strip("/") for p in cleaned)


def remote_relative(target: dict[str, Any], usb_path: str, when: float, hostname: str) -> str:
    """Path of the file relative to the target base path."""
    options = target["options"]
    sub = render_subfolder(options.get("subfolder", ""), when, hostname)
    name = usb_path if options.get("keep_structure", True) else usb_path.rsplit("/", 1)[-1]
    return join_remote(sub, name)


SecretCallback = Callable[[dict[str, str]], None]
SecretLoader = Callable[[], str]


class Transport:
    def __init__(self, target: dict[str, Any], password: str, paths: Paths,
                 on_secret: SecretCallback | None = None, reload: SecretLoader | None = None):
        self.target = target
        self.password = password
        self.paths = paths
        self.options = {**DEFAULT_OPTIONS, **(target.get("options") or {})}
        # Decoded secret: {"password": ...} or the cloud fields (token, ...).
        self.secret = load_secret(target["protocol"], password)
        # Called with changed secret values (refreshed tokens) after a run.
        self.on_secret = on_secret
        # Returns the currently stored secret; used to pick up a token that
        # another run refreshed in the meantime.
        self.reload = reload

    def put(self, local: Path, rel: str) -> str:
        """Upload local to <target path>/<rel>; return the full remote path."""
        raise NotImplementedError

    def test(self) -> list[str]:
        """Check connectivity and write access; return log lines."""
        raise NotImplementedError


class LocalTransport(Transport):
    def _base(self) -> Path:
        base = Path(self.target["path"] or "")
        if not base.is_absolute():
            raise TransferError("Local targets need an absolute path.")
        return base

    def put(self, local: Path, rel: str) -> str:
        dest = self._base() / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(f".{dest.name}.partial")
        try:
            shutil.copy2(local, tmp)
            os.replace(tmp, dest)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise TransferError(str(exc)) from exc
        return str(dest)

    def test(self) -> list[str]:
        base = self._base()
        try:
            base.mkdir(parents=True, exist_ok=True)
            probe = base / ".netusbflash-test"
            probe.write_text("ok")
            probe.unlink()
        except OSError as exc:
            raise TransferError(str(exc)) from exc
        return [f"Wrote and removed a test file in {base}"]


class RcloneTransport(Transport):
    SECTION = "target"

    def _obscure(self, value: str) -> str:
        return run(["rclone", "obscure", "-"], input_text=value, timeout=15).strip()

    def config_text(self) -> str:
        t = self.target
        proto = t["protocol"]
        port = t.get("port") or DEFAULT_PORTS.get(proto)
        lines = [f"[{self.SECTION}]"]

        def add(key: str, value: Any) -> None:
            if value not in (None, ""):
                lines.append(f"{key} = {value}")

        if proto == "smb":
            add("type", "smb")
            add("host", t["host"])
            add("port", port)
            add("user", t["username"])
            if self.password:
                add("pass", self._obscure(self.password))
            add("domain", self.options.get("domain"))
        elif proto == "webdav":
            add("type", "webdav")
            add("url", t["host"])
            add("vendor", self.options.get("vendor") or "other")
            add("user", t["username"])
            if self.password:
                add("pass", self._obscure(self.password))
        elif proto in ("ftp", "ftps"):
            add("type", "ftp")
            add("host", t["host"])
            add("port", port)
            add("user", t["username"] or "anonymous")
            if self.password:
                add("pass", self._obscure(self.password))
            if proto == "ftps":
                if self.options.get("tls_mode") == "implicit":
                    add("tls", "true")
                else:
                    add("explicit_tls", "true")
                if self.options.get("insecure_tls"):
                    add("no_check_certificate", "true")
        elif proto in ("sftp", "sshfs"):
            add("type", "sftp")
            add("host", t["host"])
            add("port", port)
            add("user", t["username"])
            if self.options.get("auth") == "key":
                add("key_file", str(self.paths.ssh_key))
            elif self.password:
                add("pass", self._obscure(self.password))
            add("known_hosts_file", str(self.paths.known_hosts) if self.paths.known_hosts.exists() else "")
        elif proto in ("dropbox", "onedrive", "gdrive", "box"):
            add("type", RCLONE_BACKENDS[proto])
            add("client_id", self.options.get("client_id"))
            add("client_secret", self.secret.get("client_secret"))
            if proto == "gdrive":
                add("scope", "drive")
                add("root_folder_id", self.options.get("root_folder_id"))
                add("team_drive", self.options.get("team_drive"))
            elif proto == "onedrive":
                add("drive_id", self.options.get("drive_id"))
                add("drive_type", self.options.get("drive_type"))
            add("token", self.secret.get("token"))
        elif proto == "icloud":
            add("type", RCLONE_BACKENDS[proto])
            add("apple_id", t["username"])
            if self.secret.get("password"):
                add("pass", self._obscure(self.secret["password"]))
            add("trust_token", self.secret.get("trust_token"))
            add("cookies", self.secret.get("cookies"))
        else:
            raise TransferError(f"Unsupported protocol for rclone: {proto}")
        return "\n".join(lines) + "\n"

    def _flags(self) -> list[str]:
        flags = ["--retries", "1", "--low-level-retries", "3", "--contimeout", "20s",
                 "--timeout", "120s", "--stats", "0"]
        if self.target["protocol"] == "webdav" and self.options.get("insecure_tls"):
            flags.append("--no-check-certificate")
        if self.options.get("bwlimit"):
            flags += ["--bwlimit", str(self.options["bwlimit"])]
        return flags

    def _check_ready(self) -> None:
        proto = self.target["protocol"]
        if proto in ("dropbox", "onedrive", "gdrive", "box") and not self.secret.get("token"):
            raise TransferError("No access token stored. Create one with rclone authorize and paste it.")
        if proto == "onedrive" and not self.options.get("drive_id"):
            raise TransferError("The OneDrive drive ID is unknown. Paste a fresh token or enter the drive ID.")
        if proto == "icloud" and not self.secret.get("trust_token"):
            raise TransferError("Not signed in to iCloud yet. Save the target and use \"Sign in to iCloud\".")

    def _rclone(self, args: list[str], input_text: str | None = None, timeout: float = 6 * 3600) -> str:
        if not which("rclone"):
            raise TransferError("rclone is not installed.")
        proto = self.target["protocol"]
        if proto not in CLOUD_PROTOCOLS:
            return self._rclone_run(args, input_text, timeout)
        self._check_ready()
        with _target_lock(self.target.get("id") or id(self)):
            if self.reload is not None:
                fresh = load_secret(proto, self.reload())
                if fresh:
                    self.secret = fresh
            return self._rclone_run(args, input_text, timeout)

    def _rclone_run(self, args: list[str], input_text: str | None, timeout: float) -> str:
        self.paths.run.mkdir(parents=True, exist_ok=True)
        fd, conf = tempfile.mkstemp(prefix="rclone-", suffix=".conf", dir=self.paths.run)
        try:
            with os.fdopen(fd, "w") as handle:
                handle.write(self.config_text())
            os.chmod(conf, 0o600)
            return run(["rclone", "--config", conf, *args, *self._flags()],
                       input_text=input_text, timeout=timeout)
        except CommandError as exc:
            raise TransferError(_rclone_error(exc.output)) from exc
        finally:
            self._write_back(conf)
            os.unlink(conf)

    def _write_back(self, conf: str) -> None:
        """Keep tokens and cookies that rclone refreshed during the run."""
        keys = WRITEBACK_KEYS.get(self.target["protocol"])
        if not keys:
            return
        try:
            values = read_rclone_section(Path(conf).read_text(), self.SECTION)
        except OSError:
            return
        changes = {k: values[k] for k in keys if values.get(k) and values[k] != self.secret.get(k)}
        if not changes:
            return
        self.secret.update(changes)
        if self.on_secret is not None:
            self.on_secret(changes)

    def _remote(self, rel: str = "") -> str:
        return f"{self.SECTION}:{join_remote(self.target['path'] or '', rel)}"

    def put(self, local: Path, rel: str) -> str:
        remote = self._remote(rel)
        self._rclone(["copyto", str(local), remote])
        return remote.split(":", 1)[1]

    def test(self) -> list[str]:
        log = []
        base = self._remote()
        self._rclone(["mkdir", base], timeout=120)
        log.append("Connected and ensured the target folder exists")
        probe = self._remote(".netusbflash-test")
        self._rclone(["rcat", probe], input_text="ok", timeout=120)
        log.append("Wrote a test file")
        self._rclone(["deletefile", probe], timeout=120)
        log.append("Deleted the test file")
        listing = self._rclone(["lsjson", "--max-depth", "1", base], timeout=120)
        try:
            count = len(json.loads(listing or "[]"))
            log.append(f"Listed the target folder ({count} entries)")
        except json.JSONDecodeError:
            pass
        return log


class ScpTransport(Transport):
    def _ssh_options(self) -> list[str]:
        opts = [
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", f"UserKnownHostsFile={self.paths.known_hosts}",
            "-o", "ConnectTimeout=20",
        ]
        if self.options.get("auth") == "key":
            opts += ["-o", "BatchMode=yes", "-i", str(self.paths.ssh_key)]
        else:
            opts += ["-o", "PreferredAuthentications=password,keyboard-interactive",
                     "-o", "PubkeyAuthentication=no", "-o", "NumberOfPasswordPrompts=1"]
        return opts

    def _wrap(self, cmd: list[str]) -> tuple[list[str], dict[str, str]]:
        if self.options.get("auth") == "key":
            return cmd, {}
        if not which("sshpass"):
            raise TransferError("Password login for SCP needs 'sshpass'. Use key authentication instead.")
        return ["sshpass", "-e", *cmd], {"SSHPASS": self.password}

    def _dest(self) -> str:
        return f"{self.target['username']}@{self.target['host']}" if self.target["username"] else self.target["host"]

    @staticmethod
    def _safe(path: str) -> str:
        return _SCP_SAFE.sub("_", path)

    def _ssh(self, remote_cmd: list[str]) -> str:
        port = str(self.target.get("port") or 22)
        cmd, env = self._wrap(["ssh", *self._ssh_options(), "-p", port, self._dest(), "--", *remote_cmd])
        try:
            return run(cmd, env=env, timeout=120)
        except CommandError as exc:
            raise TransferError(_short_error(exc.output)) from exc

    def put(self, local: Path, rel: str) -> str:
        remote = self._safe(join_remote(self.target["path"] or "", rel))
        directory = remote.rsplit("/", 1)[0] if "/" in remote else ""
        if directory:
            self._ssh(["mkdir", "-p", directory])
        port = str(self.target.get("port") or 22)
        cmd, env = self._wrap(["scp", *self._ssh_options(), "-P", port, "-q", str(local),
                               f"{self._dest()}:{remote}"])
        try:
            run(cmd, env=env, timeout=6 * 3600)
        except CommandError as exc:
            raise TransferError(_short_error(exc.output)) from exc
        return remote

    def test(self) -> list[str]:
        base = self._safe(self.target["path"] or ".")
        self._ssh(["mkdir", "-p", base])
        self._ssh(["test", "-w", base])
        return [f"Logged in via SSH and verified that {base} is writable"]


def _rclone_error(output: str) -> str:
    if "didn't find backend called" in output:
        name = output.split("didn't find backend called", 1)[1].strip().split()[0].strip('"\'')
        hint = f" iCloud Drive needs rclone {ICLOUD_MIN_RCLONE} or newer." if name == "iclouddrive" else ""
        return f"The installed rclone does not support the backend \"{name}\".{hint}"
    return _short_error(output)


class ICloudLogin:
    """Interactive iCloud sign-in with a two-factor code.

    rclone's config state machine is driven non-interactively: the first step
    signs in with Apple ID and password and asks for the 2FA code; the second
    step sends the code. In between, rclone keeps the session cookies in a
    config file, which is kept in the run directory for that time.
    """

    SECTION = "target"

    def __init__(self, target: dict[str, Any], password: str, paths: Paths):
        self.target = target
        self.paths = paths
        self.secret = load_secret("icloud", password)
        key = target.get("id") or "new"
        self.conf = paths.run / f"icloud-login-{key}.conf"
        self.state_file = paths.run / f"icloud-login-{key}.state"

    def _rclone(self, args: list[str]) -> dict[str, Any]:
        if not which("rclone"):
            raise TransferError("rclone is not installed.")
        try:
            output = run(["rclone", "--config", str(self.conf), *args, "--non-interactive"], timeout=120)
        except CommandError as exc:
            raise TransferError(_rclone_error(exc.output)) from exc
        try:
            return parse_config_answer(output)
        except CloudError as exc:
            raise TransferError(str(exc)) from exc

    def cleanup(self) -> None:
        self.conf.unlink(missing_ok=True)
        self.state_file.unlink(missing_ok=True)

    def start(self) -> dict[str, Any]:
        """Sign in. Returns {"status": "code_required"} or {"status": "ok", "secret": {...}}."""
        apple_id = self.target.get("username") or ""
        if not apple_id or not self.secret.get("password"):
            raise TransferError("Apple ID and password are required.")
        if not which("rclone"):
            raise TransferError("rclone is not installed.")
        self.paths.run.mkdir(parents=True, exist_ok=True)
        self.cleanup()
        try:
            obscured = run(["rclone", "obscure", "-"], input_text=self.secret["password"], timeout=15).strip()
        except CommandError as exc:
            raise TransferError(_short_error(exc.output)) from exc
        fd = os.open(self.conf, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(f"[{self.SECTION}]\ntype = iclouddrive\napple_id = {apple_id}\npass = {obscured}\n")
        try:
            answer = self._rclone(["config", "update", self.SECTION, "apple_id", apple_id])
            return self._handle(answer)
        except BaseException:
            self.cleanup()
            raise

    def submit_code(self, code: str) -> dict[str, Any]:
        if not self.conf.exists() or not self.state_file.exists():
            raise TransferError("The sign-in has expired. Start it again.")
        state = self.state_file.read_text()
        try:
            answer = self._rclone(["config", "update", self.SECTION, "--continue",
                                   "--state", state, "--result", code])
            return self._handle(answer)
        except BaseException:
            self.cleanup()
            raise

    def _handle(self, answer: dict[str, Any]) -> dict[str, Any]:
        # Options other than the 2FA code are answered with their default.
        for _ in range(5):
            if answer.get("Error"):
                raise TransferError(str(answer["Error"])[-400:])
            option = answer.get("Option")
            if not option:
                values = read_rclone_section(self.conf.read_text(), self.SECTION)
                self.cleanup()
                if not values.get("trust_token"):
                    raise TransferError("iCloud did not return a session. Try again.")
                return {"status": "ok", "secret": {"trust_token": values["trust_token"],
                                                   "cookies": values.get("cookies", "")}}
            if option.get("Name") == "config_2fa":
                fd = os.open(self.state_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "w") as handle:
                    handle.write(str(answer.get("State") or ""))
                return {"status": "code_required"}
            default = option.get("Default")
            answer = self._rclone(["config", "update", self.SECTION, "--continue",
                                   "--state", str(answer.get("State") or ""),
                                   "--result", "" if default is None else str(default)])
        raise TransferError("The iCloud sign-in did not finish.")


def _short_error(output: str) -> str:
    lines = [ln.strip() for ln in output.splitlines() if ln.strip()]
    for line in reversed(lines):
        if "ERROR" in line or "Permission denied" in line or "error" in line.lower():
            return line[-400:]
    return (lines[-1] if lines else "unknown error")[-400:]


def make_transport(target: dict[str, Any], password: str, paths: Paths,
                   on_secret: SecretCallback | None = None, reload: SecretLoader | None = None) -> Transport:
    proto = target["protocol"]
    if proto == "local":
        return LocalTransport(target, password, paths, on_secret, reload)
    if proto == "scp":
        return ScpTransport(target, password, paths, on_secret, reload)
    if proto in PROTOCOLS:
        return RcloneTransport(target, password, paths, on_secret, reload)
    raise TransferError(f"Unknown protocol: {proto}")

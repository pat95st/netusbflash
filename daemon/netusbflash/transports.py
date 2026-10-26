"""Upload transports for each supported protocol.

rclone handles SMB/CIFS, WebDAV (incl. Nextcloud), FTP, FTPS and SFTP.
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
import time
from pathlib import Path
from typing import Any

from .config import Paths
from .system import CommandError, run, which

PROTOCOLS = ("smb", "webdav", "ftp", "ftps", "sftp", "sshfs", "scp", "local")
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
}

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


class Transport:
    def __init__(self, target: dict[str, Any], password: str, paths: Paths):
        self.target = target
        self.password = password
        self.paths = paths
        self.options = {**DEFAULT_OPTIONS, **(target.get("options") or {})}

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

    def _rclone(self, args: list[str], input_text: str | None = None, timeout: float = 6 * 3600) -> str:
        if not which("rclone"):
            raise TransferError("rclone is not installed.")
        self.paths.run.mkdir(parents=True, exist_ok=True)
        fd, conf = tempfile.mkstemp(prefix="rclone-", suffix=".conf", dir=self.paths.run)
        try:
            with os.fdopen(fd, "w") as handle:
                handle.write(self.config_text())
            os.chmod(conf, 0o600)
            return run(["rclone", "--config", conf, *args, *self._flags()],
                       input_text=input_text, timeout=timeout)
        except CommandError as exc:
            raise TransferError(_short_error(exc.output)) from exc
        finally:
            os.unlink(conf)

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


def _short_error(output: str) -> str:
    lines = [ln.strip() for ln in output.splitlines() if ln.strip()]
    for line in reversed(lines):
        if "ERROR" in line or "Permission denied" in line or "error" in line.lower():
            return line[-400:]
    return (lines[-1] if lines else "unknown error")[-400:]


def make_transport(target: dict[str, Any], password: str, paths: Paths) -> Transport:
    proto = target["protocol"]
    if proto == "local":
        return LocalTransport(target, password, paths)
    if proto == "scp":
        return ScpTransport(target, password, paths)
    if proto in PROTOCOLS:
        return RcloneTransport(target, password, paths)
    raise TransferError(f"Unknown protocol: {proto}")

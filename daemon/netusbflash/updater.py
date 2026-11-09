"""Software updates from GitHub releases and operating system updates via apt.

Software: the latest release of the configured repository is compared with
the installed version. A release should carry an asset
`netusbflash-<version>.tar.gz` and its `.sha256` file (built by
.github/workflows/release.yml); otherwise the source tarball of the tag is
used. The archive is unpacked and `packaging/install.sh --upgrade` runs as a
transient systemd unit, so the update survives the restart of this service.

Operating system: `apt-get update` plus `apt-get full-upgrade` in a transient
systemd unit. Its output goes to a log file the web interface shows.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import tarfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import __version__
from .system import CommandError, run, which

if TYPE_CHECKING:
    from .service import Context

log = logging.getLogger(__name__)

DEFAULT_UPDATE: dict[str, Any] = {
    "repository": "pat95st/netusbflash",
    "prereleases": True,
    "auto_check": True,
}
CHECK_INTERVAL = 24 * 3600
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
MAX_DOWNLOAD = 200 * 1024 * 1024


class UpdateError(Exception):
    pass


_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")


def parse_version(value: str) -> tuple | None:
    """Semantic version as a sortable tuple; None if it is not one."""
    m = _VERSION_RE.match((value or "").strip())
    if not m:
        return None
    major, minor, patch, pre = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
    if pre is None:
        return (major, minor, patch, 1, ())
    parts = tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in pre.split("."))
    return (major, minor, patch, 0, parts)


def is_newer(candidate: str, current: str) -> bool:
    a, b = parse_version(candidate), parse_version(current)
    return a is not None and b is not None and a > b


def pick_release(releases: list[dict[str, Any]], prereleases: bool) -> dict[str, Any] | None:
    best, best_key = None, None
    for release in releases:
        if release.get("draft") or (release.get("prerelease") and not prereleases):
            continue
        key = parse_version(release.get("tag_name", ""))
        if key is not None and (best_key is None or key > best_key):
            best, best_key = release, key
    return best


def safe_extract(archive: Path, dest: Path) -> Path:
    """Unpack a tar.gz without absolute paths, '..' or links; return the project root."""
    dest.mkdir(parents=True, exist_ok=True)
    root = dest.resolve()
    with tarfile.open(archive, "r:gz") as tar:
        members = []
        for member in tar.getmembers():
            target = (root / member.name).resolve()
            if not str(target).startswith(str(root) + "/") and target != root:
                raise UpdateError(f"Unsafe path in archive: {member.name}")
            if member.issym() or member.islnk() or member.isdev():
                continue
            members.append(member)
        try:
            tar.extractall(root, members=members, filter="data")
        except TypeError:  # Python without extraction filters
            tar.extractall(root, members=members)
    for candidate in [root, *sorted(p for p in root.iterdir() if p.is_dir())]:
        if (candidate / "packaging" / "install.sh").is_file() and (candidate / "VERSION").is_file():
            return candidate
    raise UpdateError("The archive does not contain packaging/install.sh.")


class Updater(threading.Thread):
    def __init__(self, ctx: "Context"):
        super().__init__(name="updater", daemon=True)
        self.ctx = ctx
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.os_check_running = False

    # Settings and state ----------------------------------------------------

    def settings(self) -> dict[str, Any]:
        return self.ctx.db.get_dict_setting("update", DEFAULT_UPDATE)

    @property
    def log_file(self) -> Path:
        return self.ctx.paths.updates / "update.log"

    @property
    def job_file(self) -> Path:
        return self.ctx.paths.updates / "job.json"

    def job(self) -> dict[str, Any] | None:
        try:
            job = json.loads(self.job_file.read_text())
        except (OSError, json.JSONDecodeError):
            return None
        job["active"] = self._unit_active(job)
        return job

    def _unit_active(self, job: dict[str, Any]) -> bool:
        if self.ctx.simulated:
            return time.time() - job.get("started", 0) < 3
        try:
            state = run(["systemctl", "show", "-p", "ActiveState", "--value", job["unit"]], timeout=10).strip()
        except CommandError:
            return False
        return state in ("active", "activating", "deactivating")

    def log_tail(self, lines: int = 200) -> str:
        try:
            content = self.log_file.read_text(errors="replace")
        except OSError:
            return ""
        return "\n".join(content.splitlines()[-lines:])

    def status(self) -> dict[str, Any]:
        info = self.ctx.db.get_setting("update_info", {}) or {}
        latest = info.get("latest")
        return {
            "current": __version__,
            "settings": self.settings(),
            "latest": latest,
            "update_available": bool(latest and is_newer(latest.get("version", ""), __version__)),
            "last_check": info.get("checked"),
            "check_error": info.get("error", ""),
            "os": self.ctx.db.get_setting("os_update_info", {}) or {},
            "os_check_running": self.os_check_running,
            "reboot_required": Path("/var/run/reboot-required").exists(),
            "job": self.job(),
            "log": self.log_tail(),
            "simulated": self.ctx.simulated,
        }

    # Software: check ---------------------------------------------------------

    def _http(self, url: str, timeout: float = 20) -> urllib.request.Request:
        return urllib.request.Request(url, headers={
            "User-Agent": f"netusbflash/{__version__}",
            "Accept": "application/vnd.github+json",
        })

    def check(self) -> dict[str, Any]:
        cfg = self.settings()
        repo = cfg["repository"]
        if not REPO_RE.match(repo):
            raise UpdateError("Invalid repository name.")
        url = f"https://api.github.com/repos/{repo}/releases?per_page=30"
        try:
            with urllib.request.urlopen(self._http(url), timeout=20) as resp:
                releases = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            self.ctx.db.set_setting("update_info", {"checked": time.time(), "error": str(exc),
                                                    "latest": (self.ctx.db.get_setting("update_info", {}) or {}).get("latest")})
            raise UpdateError(f"Could not reach GitHub: {exc}") from exc
        release = pick_release(releases if isinstance(releases, list) else [], bool(cfg["prereleases"]))
        latest = None
        if release:
            version = release["tag_name"].lstrip("v")
            assets = {a.get("name"): a.get("browser_download_url") for a in release.get("assets", [])}
            latest = {
                "version": version,
                "name": release.get("name") or release["tag_name"],
                "notes": (release.get("body") or "")[:20000],
                "published_at": release.get("published_at"),
                "url": release.get("html_url"),
                "prerelease": bool(release.get("prerelease")),
                "archive": assets.get(f"netusbflash-{version}.tar.gz") or release.get("tarball_url"),
                "sha256": assets.get(f"netusbflash-{version}.tar.gz.sha256"),
            }
        previous = (self.ctx.db.get_setting("update_info", {}) or {}).get("latest") or {}
        self.ctx.db.set_setting("update_info", {"checked": time.time(), "error": "", "latest": latest})
        if latest and is_newer(latest["version"], __version__) and previous.get("version") != latest["version"]:
            self.ctx.db.log("info", "update", f"Update available: {latest['version']} (installed {__version__})")
        return self.status()

    # Jobs ----------------------------------------------------------------------

    def _start_job(self, kind: str, script: str, version: str = "") -> dict[str, Any]:
        with self.lock:
            current = self.job()
            if current and current["active"]:
                raise UpdateError("An update is already running.")
            unit = f"netusbflash-{kind}-update-{int(time.time())}"
            self.log_file.write_text(f"=== {time.strftime('%Y-%m-%d %H:%M:%S')} {kind} update started ===\n")
            job = {"kind": kind, "unit": unit, "started": time.time(), "version": version}
            self.job_file.write_text(json.dumps(job))
            if self.ctx.simulated:
                with self.log_file.open("a") as handle:
                    handle.write("Simulation mode: nothing is installed.\n")
                return self.status()
            if not which("systemd-run"):
                raise UpdateError("systemd-run is not available.")
            run(["systemd-run", "--unit", unit, "--collect", "--quiet",
                 "--property", "Type=oneshot",
                 "/bin/bash", "-c", f"{script} >> {self.log_file} 2>&1"], timeout=30)
        self.ctx.db.log("info", "update", f"{kind.capitalize()} update started ({unit})")
        return self.status()

    def install_software(self) -> dict[str, Any]:
        info = (self.ctx.db.get_setting("update_info", {}) or {}).get("latest")
        if not info or not info.get("archive"):
            raise UpdateError("No release found. Check for updates first.")
        if not is_newer(info["version"], __version__):
            raise UpdateError("The installed version is up to date.")
        work = self.ctx.paths.updates / info["version"]
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        archive = work / "release.tar.gz"
        if self.ctx.simulated:
            return self._start_job("software", "true", info["version"])
        self._download(info["archive"], archive)
        if info.get("sha256"):
            expected = self._read_checksum(info["sha256"])
            actual = hashlib.sha256(archive.read_bytes()).hexdigest()
            if expected != actual:
                raise UpdateError("Checksum mismatch: the download is damaged or was altered.")
        root = safe_extract(archive, work / "src")
        version = (root / "VERSION").read_text().strip()
        if version.lstrip("v") != info["version"]:
            raise UpdateError(f"The archive contains version {version}, expected {info['version']}.")
        script = f"bash {root}/packaging/install.sh --upgrade"
        return self._start_job("software", script, info["version"])

    def install_os(self) -> dict[str, Any]:
        script = ("export DEBIAN_FRONTEND=noninteractive; "
                  "apt-get update && "
                  "apt-get -y -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold full-upgrade && "
                  "apt-get -y autoremove")
        return self._start_job("os", script)

    def check_os(self) -> dict[str, Any]:
        """Refresh package lists and count upgradable packages (in the background)."""
        if self.os_check_running:
            return self.status()
        self.os_check_running = True

        def worker() -> None:
            try:
                if self.ctx.simulated:
                    packages = ["example-package/stable 1.2.3 arm64 [upgradable from: 1.2.2]"]
                else:
                    run(["apt-get", "update", "-q"], timeout=600)
                    out = run(["apt", "list", "--upgradable"], timeout=120, env={"LC_ALL": "C"})
                    packages = [ln for ln in out.splitlines() if "/" in ln and "upgradable" in ln]
                self.ctx.db.set_setting("os_update_info", {
                    "checked": time.time(), "count": len(packages),
                    "packages": [p.split("/", 1)[0] for p in packages[:100]], "error": "",
                })
            except CommandError as exc:
                self.ctx.db.set_setting("os_update_info", {"checked": time.time(), "count": None,
                                                           "packages": [], "error": exc.output[-500:]})
            finally:
                self.os_check_running = False

        threading.Thread(target=worker, daemon=True).start()
        return self.status()

    def _download(self, url: str, dest: Path) -> None:
        try:
            with urllib.request.urlopen(self._http(url), timeout=60) as resp, dest.open("wb") as handle:
                total = 0
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD:
                        raise UpdateError("The download is unexpectedly large.")
                    handle.write(chunk)
        except (urllib.error.URLError, OSError) as exc:
            raise UpdateError(f"Download failed: {exc}") from exc

    def _read_checksum(self, url: str) -> str:
        try:
            with urllib.request.urlopen(self._http(url), timeout=30) as resp:
                text = resp.read(4096).decode("utf-8", "replace")
        except (urllib.error.URLError, OSError) as exc:
            raise UpdateError(f"Checksum download failed: {exc}") from exc
        value = text.split()[0] if text.split() else ""
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise UpdateError("The checksum file is invalid.")
        return value

    # Worker: daily check -----------------------------------------------------

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        self.stop_event.wait(120)  # let the network come up after boot
        while not self.stop_event.is_set():
            info = self.ctx.db.get_setting("update_info", {}) or {}
            if self.settings()["auto_check"] and time.time() - (info.get("checked") or 0) > CHECK_INTERVAL:
                try:
                    self.check()
                except UpdateError as exc:
                    log.info("update check failed: %s", exc)
            self.stop_event.wait(3600)

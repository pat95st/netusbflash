"""System helpers: running commands safely and reading device information."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Sequence


class CommandError(Exception):
    def __init__(self, cmd: Sequence[str], returncode: int, output: str):
        self.cmd = list(cmd)
        self.returncode = returncode
        self.output = output.strip()
        super().__init__(f"{cmd[0]} failed ({returncode}): {self.output[-500:]}")


def run(cmd: Sequence[str], *, input_text: str | None = None, timeout: float = 120,
        env: dict[str, str] | None = None, check: bool = True) -> str:
    """Run a command without a shell and return combined output.

    Arguments are always passed as a list, so user input can never be
    interpreted by a shell.
    """
    full_env = dict(os.environ)
    full_env["LC_ALL"] = "C"
    if env:
        full_env.update(env)
    try:
        proc = subprocess.run(
            list(cmd), input=input_text, capture_output=True, text=True,
            timeout=timeout, env=full_env, check=False,
        )
    except FileNotFoundError as exc:
        raise CommandError(cmd, 127, f"command not found: {cmd[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise CommandError(cmd, 124, f"timeout after {timeout}s") from exc
    output = (proc.stdout or "") + (proc.stderr or "")
    if check and proc.returncode != 0:
        raise CommandError(cmd, proc.returncode, output)
    return output


def which(name: str) -> bool:
    return shutil.which(name) is not None


def pi_model() -> str:
    try:
        return Path("/proc/device-tree/model").read_text(errors="ignore").strip("\x00\n ")
    except OSError:
        return "unknown"


def cpu_temperature() -> float | None:
    try:
        return int(Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()) / 1000.0
    except (OSError, ValueError):
        return None


def uptime_seconds() -> float | None:
    try:
        return float(Path("/proc/uptime").read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return None


def disk_usage(path: Path) -> dict[str, int]:
    usage = shutil.disk_usage(path)
    return {"total": usage.total, "used": usage.used, "free": usage.free}


def hostname() -> str:
    return socket.gethostname()


def ip_addresses() -> list[str]:
    try:
        out = run(["hostname", "-I"], timeout=5)
    except CommandError:
        return []
    return out.split()


def timezone() -> str:
    try:
        return Path("/etc/timezone").read_text().strip()
    except OSError:
        pass
    try:
        link = os.readlink("/etc/localtime")
        return link.split("zoneinfo/", 1)[1]
    except (OSError, IndexError):
        return "UTC"


def set_hostname(name: str) -> None:
    run(["hostnamectl", "set-hostname", name], timeout=30)
    # Keep /etc/hosts consistent so sudo and mDNS keep working.
    hosts = Path("/etc/hosts")
    try:
        lines = hosts.read_text().splitlines()
        lines = [ln for ln in lines if not ln.startswith("127.0.1.1")]
        lines.append(f"127.0.1.1\t{name}")
        hosts.write_text("\n".join(lines) + "\n")
    except OSError:
        pass


def set_timezone(name: str) -> None:
    run(["timedatectl", "set-timezone", name], timeout=30)


def list_timezones() -> list[str]:
    try:
        return run(["timedatectl", "list-timezones"], timeout=15).split()
    except CommandError:
        return ["UTC", "Europe/Berlin", "Europe/Vienna", "Europe/Zurich", "Europe/London"]


def reboot() -> None:
    run(["systemctl", "reboot"], timeout=30)


def poweroff() -> None:
    run(["systemctl", "poweroff"], timeout=30)

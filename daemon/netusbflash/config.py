"""Runtime paths and environment switches.

Production paths follow the Debian layout. For development and tests, set
NETUSBFLASH_HOME to a directory; all state is then kept below it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    etc: Path
    lib: Path
    run: Path

    @property
    def db(self) -> Path:
        return self.lib / "state.db"

    @property
    def secret_key(self) -> Path:
        return self.etc / "secret.key"

    @property
    def setup_token(self) -> Path:
        return self.etc / "setup-token"

    @property
    def socket(self) -> Path:
        return Path(os.environ.get("NETUSBFLASH_SOCKET", str(self.run / "api.sock")))

    @property
    def spool(self) -> Path:
        return self.lib / "spool"

    @property
    def mountpoint(self) -> Path:
        return self.run / "usb"

    @property
    def ssh_dir(self) -> Path:
        return self.lib / "ssh"

    @property
    def ssh_key(self) -> Path:
        return self.ssh_dir / "id_ed25519"

    @property
    def known_hosts(self) -> Path:
        return self.ssh_dir / "known_hosts"

    @property
    def image(self) -> Path:
        return self.lib / "usb.img"

    @property
    def sim_dir(self) -> Path:
        """Directory that stands in for the USB stick in simulation mode."""
        return self.lib / "usb-sim"

    def ensure(self) -> None:
        for directory, mode in (
            (self.etc, 0o750),
            (self.lib, 0o750),
            (self.run, 0o755),
            (self.spool, 0o750),
            (self.ssh_dir, 0o700),
        ):
            directory.mkdir(parents=True, exist_ok=True)
            try:
                directory.chmod(mode)
            except PermissionError:
                pass


def load_paths() -> Paths:
    home = os.environ.get("NETUSBFLASH_HOME")
    if home:
        base = Path(home).resolve()
        return Paths(etc=base / "etc", lib=base / "lib", run=base / "run")
    return Paths(
        etc=Path("/etc/netusbflash"),
        lib=Path("/var/lib/netusbflash"),
        run=Path("/run/netusbflash"),
    )


def simulate() -> bool:
    """True when the USB gadget should be simulated with a plain directory."""
    return os.environ.get("NETUSBFLASH_SIMULATE", "") == "1"


SOCKET_GROUP = os.environ.get("NETUSBFLASH_SOCKET_GROUP", "netusbflash")

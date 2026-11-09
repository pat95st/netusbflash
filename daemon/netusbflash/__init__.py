"""NetUSBFlash: emulate a USB stick on a Raspberry Pi and upload recordings to network storage."""

from pathlib import Path


def _read_version() -> str:
    # Installed: /opt/netusbflash/VERSION; repository: <repo>/VERSION.
    for candidate in (Path(__file__).resolve().parents[2] / "VERSION",):
        try:
            value = candidate.read_text().strip()
        except OSError:
            continue
        if value:
            return value
    return "0.0.0-dev"


__version__ = _read_version()

"""USB mass-storage gadget.

The Pi presents a disk image to the USB host (e.g. a mixing console) through
the Linux USB gadget framework (configfs + libcomposite + dwc2). The image
holds an MBR partition table with one FAT32 or exFAT partition, like a normal
USB stick.

In simulation mode (NETUSBFLASH_SIMULATE=1) a plain directory stands in for
the stick, which makes development and tests possible on any machine.
"""

from __future__ import annotations

import os
import secrets
import shutil
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .config import Paths
from .system import CommandError, run

GADGET_NAME = "netusbflash"
CONFIGFS = Path("/sys/kernel/config/usb_gadget")
UDC_CLASS = Path("/sys/class/udc")
PARTITION_OFFSET = 1024 * 1024  # first partition starts at sector 2048

DEFAULT_USB: dict[str, Any] = {
    "enabled": True,
    "size_mb": 4096,
    "filesystem": "exfat",          # exfat | vfat
    "label": "RECORDINGS",
    "partition_table": True,
    "removable": True,
    "read_only": False,
    "cdrom": False,
    "vendor_id": "0x1d6b",          # Linux Foundation
    "product_id": "0x0104",         # Multifunction Composite Gadget
    "manufacturer": "NetUSBFlash",
    "product": "USB Recorder Storage",
    "serial": "",
    "max_power_ma": 100,
    "sync_mode": "detach",          # detach | live
    "idle_seconds": 30,
    "delete_after_upload": False,
    "include": "*",
    "exclude": "",
}

FILESYSTEMS = ("exfat", "vfat")
SYNC_MODES = ("detach", "live")


class GadgetError(Exception):
    pass


class GadgetBackend:
    """Interface shared by the real and the simulated gadget."""

    def __init__(self, paths: Paths):
        self.paths = paths
        self.lock = threading.RLock()

    def available(self) -> tuple[bool, str]:
        raise NotImplementedError

    def state(self) -> dict[str, Any]:
        raise NotImplementedError

    def image_exists(self) -> bool:
        raise NotImplementedError

    def image_info(self) -> dict[str, Any]:
        raise NotImplementedError

    def create_image(self, cfg: dict[str, Any]) -> None:
        raise NotImplementedError

    def apply(self, cfg: dict[str, Any]) -> None:
        raise NotImplementedError

    def attach(self) -> None:
        raise NotImplementedError

    def detach(self) -> None:
        raise NotImplementedError

    def teardown(self) -> None:
        raise NotImplementedError

    def last_write(self) -> float:
        raise NotImplementedError

    @contextmanager
    def mount(self, writable: bool) -> Iterator[Path]:
        raise NotImplementedError
        yield  # pragma: no cover


def _write(path: Path, value: Any) -> None:
    path.write_text(f"{value}\n")


class ConfigfsGadget(GadgetBackend):
    """Real USB gadget via configfs. Requires root, dwc2 and libcomposite."""

    @property
    def root(self) -> Path:
        return CONFIGFS / GADGET_NAME

    def _udc_name(self) -> str:
        try:
            names = sorted(p.name for p in UDC_CLASS.iterdir())
        except FileNotFoundError:
            names = []
        if not names:
            raise GadgetError(
                "No USB device controller found. Enable 'dtoverlay=dwc2,dr_mode=peripheral' "
                "in /boot/firmware/config.txt and reboot."
            )
        return names[0]

    def available(self) -> tuple[bool, str]:
        if os.geteuid() != 0:
            return False, "The service must run as root to control the USB gadget."
        if not CONFIGFS.exists():
            try:
                run(["modprobe", "libcomposite"], timeout=15)
            except CommandError as exc:
                return False, f"libcomposite not available: {exc.output}"
        if not CONFIGFS.exists():
            return False, "configfs USB gadget support is not available."
        try:
            self._udc_name()
        except GadgetError as exc:
            return False, str(exc)
        return True, ""

    def state(self) -> dict[str, Any]:
        configured = self.root.exists()
        udc = ""
        if configured:
            try:
                udc = (self.root / "UDC").read_text().strip()
            except OSError:
                udc = ""
        host_state = ""
        if udc:
            try:
                host_state = (UDC_CLASS / udc / "state").read_text().strip()
            except OSError:
                host_state = ""
        return {
            "configured": configured,
            "attached": bool(udc),
            "udc": udc,
            # "configured" here means the USB host has enumerated the device.
            "host_connected": host_state == "configured",
            "host_state": host_state,
            "simulated": False,
        }

    def image_exists(self) -> bool:
        return self.paths.image.exists()

    def image_info(self) -> dict[str, Any]:
        if not self.image_exists():
            return {"exists": False}
        st = self.paths.image.stat()
        return {"exists": True, "size": st.st_size, "allocated": st.st_blocks * 512, "mtime": st.st_mtime}

    def create_image(self, cfg: dict[str, Any]) -> None:
        with self.lock:
            size = int(cfg["size_mb"]) * 1024 * 1024
            free = shutil.disk_usage(self.paths.lib).free
            existing = self.paths.image.stat().st_size if self.image_exists() else 0
            if size > free + existing - 512 * 1024 * 1024:
                raise GadgetError("Not enough free space on the SD card for an image of this size.")
            self.teardown()
            tmp = self.paths.image.with_suffix(".img.tmp")
            tmp.unlink(missing_ok=True)
            with open(tmp, "wb") as handle:
                handle.truncate(size)
            fs = cfg["filesystem"]
            label = cfg["label"]
            try:
                if cfg.get("partition_table", True):
                    part_type = "7" if fs == "exfat" else "c"
                    run(["sfdisk", "--quiet", str(tmp)], input_text=f"label: dos\nstart=2048, type={part_type}\n")
                    loop = run(["losetup", "--find", "--show", "--offset", str(PARTITION_OFFSET),
                                "--sizelimit", str(size - PARTITION_OFFSET), str(tmp)]).strip()
                    try:
                        self._mkfs(fs, label, loop)
                    finally:
                        run(["losetup", "--detach", loop], check=False)
                else:
                    self._mkfs(fs, label, str(tmp))
            except CommandError:
                tmp.unlink(missing_ok=True)
                raise
            os.replace(tmp, self.paths.image)

    @staticmethod
    def _mkfs(fs: str, label: str, device: str) -> None:
        if fs == "exfat":
            run(["mkfs.exfat", "-L", label, device], timeout=600)
        else:
            run(["mkfs.vfat", "-F", "32", "-n", label, device], timeout=600)

    def apply(self, cfg: dict[str, Any]) -> None:
        """(Re)build the gadget from cfg and attach it to the USB controller."""
        with self.lock:
            if not self.image_exists():
                raise GadgetError("No disk image yet. Create one first.")
            ok, reason = self.available()
            if not ok:
                raise GadgetError(reason)
            self.teardown()
            g = self.root
            g.mkdir()
            _write(g / "idVendor", cfg["vendor_id"])
            _write(g / "idProduct", cfg["product_id"])
            _write(g / "bcdDevice", "0x0100")
            _write(g / "bcdUSB", "0x0200")
            strings = g / "strings" / "0x409"
            strings.mkdir(parents=True)
            serial = cfg.get("serial") or secrets.token_hex(8).upper()
            _write(strings / "serialnumber", serial)
            _write(strings / "manufacturer", cfg["manufacturer"])
            _write(strings / "product", cfg["product"])
            config = g / "configs" / "c.1"
            config.mkdir(parents=True)
            (config / "strings" / "0x409").mkdir(parents=True)
            _write(config / "strings" / "0x409" / "configuration", "Mass Storage")
            _write(config / "MaxPower", int(cfg.get("max_power_ma", 100)))
            func = g / "functions" / "mass_storage.usb0"
            func.mkdir(parents=True)
            _write(func / "stall", 1)
            lun = func / "lun.0"
            _write(lun / "removable", int(bool(cfg["removable"])))
            _write(lun / "ro", int(bool(cfg["read_only"])))
            _write(lun / "cdrom", int(bool(cfg["cdrom"])))
            _write(lun / "nofua", 0)
            inquiry = f"{cfg['manufacturer'][:8]:<8}{cfg['product'][:16]:<16}0100"
            try:
                _write(lun / "inquiry_string", inquiry)
            except OSError:
                pass
            _write(lun / "file", self.paths.image)
            os.symlink(func, config / "mass_storage.usb0")
            self.attach()

    def attach(self) -> None:
        with self.lock:
            if not self.root.exists():
                raise GadgetError("Gadget is not configured.")
            _write(self.root / "UDC", self._udc_name())

    def detach(self) -> None:
        with self.lock:
            udc = self.root / "UDC"
            if udc.exists() and udc.read_text().strip():
                _write(udc, "")

    def teardown(self) -> None:
        with self.lock:
            g = self.root
            if not g.exists():
                return
            self.detach()
            link = g / "configs" / "c.1" / "mass_storage.usb0"
            if link.is_symlink():
                link.unlink()
            for path in (
                g / "configs" / "c.1" / "strings" / "0x409",
                g / "configs" / "c.1",
                g / "functions" / "mass_storage.usb0",
                g / "strings" / "0x409",
                g,
            ):
                if path.exists():
                    path.rmdir()

    def last_write(self) -> float:
        try:
            return self.paths.image.stat().st_mtime
        except FileNotFoundError:
            return 0.0

    @contextmanager
    def mount(self, writable: bool) -> Iterator[Path]:
        mnt = self.paths.mountpoint
        mnt.mkdir(parents=True, exist_ok=True)
        opts = ["rw" if writable else "ro", "loop"]
        if self._has_partition_table():
            opts.append(f"offset={PARTITION_OFFSET}")
        run(["mount", "-o", ",".join(opts), str(self.paths.image), str(mnt)], timeout=60)
        try:
            yield mnt
        finally:
            run(["umount", str(mnt)], timeout=120, check=False)
            if writable:
                run(["sync"], timeout=120, check=False)

    def _has_partition_table(self) -> bool:
        try:
            with open(self.paths.image, "rb") as handle:
                handle.seek(510)
                if handle.read(2) != b"\x55\xaa":
                    return False
                handle.seek(0)
                boot = handle.read(512)
        except OSError:
            return False
        return mbr_first_partition_at_2048(boot)


def mbr_first_partition_at_2048(sector: bytes) -> bool:
    """True if sector 0 is an MBR whose first partition starts at LBA 2048.

    A FAT/exFAT boot sector also ends with 55 AA, so the signature alone is not
    enough; the OEM name and the first partition entry tell them apart.
    """
    if len(sector) < 512 or sector[510:512] != b"\x55\xaa":
        return False
    if sector[3:11] in (b"EXFAT   ", b"mkfs.fat", b"MSDOS5.0", b"MSWIN4.1"):
        return False
    part_type = sector[0x1C2]
    start_lba = int.from_bytes(sector[0x1C6:0x1CA], "little")
    return part_type in (0x07, 0x0B, 0x0C) and start_lba == 2048


class SimulatedGadget(GadgetBackend):
    """Stand-in gadget: a directory plays the role of the USB stick."""

    def __init__(self, paths: Paths):
        super().__init__(paths)
        self._configured = False
        self._attached = False

    def available(self) -> tuple[bool, str]:
        return True, ""

    def state(self) -> dict[str, Any]:
        return {
            "configured": self._configured,
            "attached": self._attached,
            "udc": "simulated" if self._attached else "",
            "host_connected": self._attached,
            "host_state": "configured" if self._attached else "",
            "simulated": True,
        }

    def image_exists(self) -> bool:
        return self.paths.sim_dir.is_dir()

    def image_info(self) -> dict[str, Any]:
        if not self.image_exists():
            return {"exists": False}
        size = sum(p.stat().st_size for p in self.paths.sim_dir.rglob("*") if p.is_file())
        return {"exists": True, "size": size, "allocated": size, "mtime": self.last_write()}

    def create_image(self, cfg: dict[str, Any]) -> None:
        with self.lock:
            if self.paths.sim_dir.exists():
                shutil.rmtree(self.paths.sim_dir)
            self.paths.sim_dir.mkdir(parents=True)

    def apply(self, cfg: dict[str, Any]) -> None:
        if not self.image_exists():
            raise GadgetError("No disk image yet. Create one first.")
        self._configured = True
        self._attached = True

    def attach(self) -> None:
        if not self._configured:
            raise GadgetError("Gadget is not configured.")
        self._attached = True

    def detach(self) -> None:
        self._attached = False

    def teardown(self) -> None:
        self._configured = False
        self._attached = False

    def last_write(self) -> float:
        root = self.paths.sim_dir
        if not root.exists():
            return 0.0
        latest = root.stat().st_mtime
        for dirpath, dirnames, filenames in os.walk(root):
            for name in dirnames + filenames:
                try:
                    latest = max(latest, os.stat(os.path.join(dirpath, name)).st_mtime)
                except FileNotFoundError:
                    pass
        return latest

    @contextmanager
    def mount(self, writable: bool) -> Iterator[Path]:
        yield self.paths.sim_dir


def make_gadget(paths: Paths, simulated: bool) -> GadgetBackend:
    return SimulatedGadget(paths) if simulated else ConfigfsGadget(paths)

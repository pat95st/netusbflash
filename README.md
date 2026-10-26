# NetUSBFlash

NetUSBFlash turns a Raspberry Pi into a **network-connected USB stick**. Plug the Pi
into the USB port of a mixing console, a field recorder or any other device that
records to a USB stick. The device records to the "stick" as usual, and
NetUSBFlash uploads every new recording to your storage over SMB/CIFS, WebDAV
(Nextcloud), FTP, FTPS, SFTP, SSHFS or SCP, and can send an email about it.

> **Status: alpha (0.1.0-alpha.1).** The software runs end to end with a
> simulated USB stick and is covered by automated tests. It has **not yet been
> tested on real Raspberry Pi hardware with a mixing console.** Expect rough
> edges, and do not rely on it as your only copy of important recordings yet.

```
 Mixing console ──USB──▶ Raspberry Pi (pretends to be a USB stick)
                              │  detects new recordings
                              ▼
                  SMB · WebDAV/Nextcloud · FTP(S) · SFTP/SSHFS · SCP
                              │
                              ▼
                     NAS, cloud or server   (+ optional email)
```

## Features in this alpha

- **USB stick emulation** with the Linux USB gadget framework: configurable size,
  exFAT or FAT32, volume label, vendor/product strings, removable and read-only
  flags.
- **Recording detection**: waits until the host has stopped writing, then picks up
  new and changed files. Two sync modes: *disconnect briefly* (safe, default) and
  *stay connected* (experimental).
- **Uploads** to any number of targets, with retries and backoff, include/exclude
  patterns, date-based subfolders, bandwidth limits and optional deletion from
  the stick after a successful upload.
- **Email notifications** via SMTP for new, changed and deleted files and for
  successful or failed uploads, instantly or as a digest, in English or German.
- **Web interface** in English and German (Bootstrap 5, served locally), reachable
  from the local network only.
- **Users with four roles**: viewer, operator, manager, administrator.
- **Setup wizard** for the first start, protected by a one-time code.

Not yet included: sharing the stick contents on the network (SMB/NFS/WebDAV
server), configuration backup/restore, MTP mode, a `.deb` package. See the
[roadmap](#roadmap).

## Hardware

The Pi must be able to act as a USB *device*. Only these models can:

| Model | USB port to the host | Power |
| --- | --- | --- |
| Raspberry Pi Zero 2 W | the "USB" data port | separate "PWR" port – easiest option |
| Raspberry Pi 4 Model B, CM4 | USB-C port | the USB-C port is also the power input: use a USB-C power/data splitter or a PoE HAT |
| Raspberry Pi 5, CM5 | USB-C port | as Pi 4; the Pi 5 needs considerably more power than a USB host port supplies |

Pi 3, Pi 400 and Pi 500/500+ cannot act as USB devices. A USB host port of a
mixing console usually supplies only 500–900 mA, which is not enough to power a
Pi 4 or Pi 5.

Raspberry Pi OS Lite (64-bit), based on Debian 13 "trixie", is the target
system; Debian 12 "bookworm" based releases should work as well.

## Quick start

On a freshly installed Raspberry Pi OS Lite with SSH enabled:

```bash
sudo apt install -y git
git clone https://github.com/pat95st/netusbflash.git
cd netusbflash
sudo ./packaging/install.sh
sudo reboot            # once, to enable USB device mode
```

Then open `https://<hostname>.local` from a computer in the same network and
follow the setup wizard. The installer prints the setup code; show it again
with `sudo netusbflash-cli setup show-code`.

The full guide is in [docs/setup.md](docs/setup.md).

## Development

You need Python 3.11+ with the `cryptography` package and PHP 8.2+ with the
`curl` and `mbstring` extensions. No Pi is required: the USB stick is simulated
with a folder.

```bash
./scripts/dev-server.sh          # service + UI on http://127.0.0.1:8080
```

Copy files into `.dev/lib/usb-sim/` to simulate recordings.

Tests:

```bash
cd daemon && python3 -m unittest discover -s tests
php web/tests/check_lang.php
```

More in [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/architecture.md](docs/architecture.md).

## Project layout

```
daemon/       Python service (runs as root): USB gadget, detection, uploads, email, API
web/          PHP web interface (runs as www-data), Bootstrap 5, EN/DE language files
packaging/    install.sh, systemd units, nginx and firewall configuration
scripts/      development helpers
docs/         setup guide, architecture, API
```

## Roadmap

1. Tests on Pi Zero 2 W, Pi 4 and Pi 5 with real mixing consoles
2. Optional network share of the stick contents (SMB, NFS, WebDAV), off by default
3. Configuration backup and restore
4. Host key verification for SFTP/SSHFS targets (currently trust on first use only for SCP)
5. `.deb` package and signed releases

## License

Not decided yet. Bootstrap and Bootstrap Icons (in `web/public/assets/vendor`)
are MIT licensed.

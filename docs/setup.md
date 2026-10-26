# NetUSBFlash setup guide

This guide takes you from a blank SD card to a Raspberry Pi that acts as a USB
stick for your mixing console and uploads recordings to your storage. Plan
about 30 minutes.

> This guide describes the alpha version 0.1.0-alpha.1. Screens and commands
> may still change.

## Before you start

| You need | Notes |
| --- | --- |
| Raspberry Pi Zero 2 W, Pi 4 or Pi 5 (or CM4/CM5) | Other models cannot act as a USB device. |
| Power supply | Zero 2 W: power on the "PWR" port. Pi 4/5: USB-C power/data splitter or PoE HAT, because the USB-C port is used for data. |
| USB cable to the console | Zero 2 W: micro-USB (data port "USB") to the console. Pi 4/5: USB-C (through the splitter) to the console. |
| microSD card, 16 GB or more | The emulated stick lives on this card, so pick the size accordingly. A2 cards are faster. |
| Network | Ethernet (Pi 4/5) or Wi-Fi. The web interface is reachable only from the local network. |
| A computer | With Raspberry Pi Imager and a web browser, in the same network. |
| Storage credentials | Address, user and password (or SSH key) of your NAS, Nextcloud or server. |

## Step 1: Prepare the SD card

1. Start [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
2. Choose your Pi model and **Raspberry Pi OS Lite (64-bit)**.
3. In the OS customisation settings, set:
    - hostname, e.g. `netusbflash`
    - a user name and a strong password (this is the Linux account, not the web interface login)
    - Wi-Fi, if you do not use Ethernet
    - time zone and keyboard layout
    - enable SSH
4. Write the card, put it into the Pi, connect power and network, and wait about
   two minutes.

Do not connect the Pi to the mixing console yet.

## Step 2: Install NetUSBFlash

Log in via SSH and run the installer:

```bash
ssh <user>@netusbflash.local
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y git
git clone https://github.com/pat95st/netusbflash.git
cd netusbflash
sudo ./packaging/install.sh
```

The installer:

- installs the required packages (Python, nginx, PHP-FPM, rclone, exFAT/FAT tools, OpenSSH client, nftables, Avahi)
- enables USB device mode (`dtoverlay=dwc2,dr_mode=peripheral` in `config.txt`, modules `dwc2` and `libcomposite`)
- copies the program to `/opt/netusbflash` and starts the `netusbflash` service
- configures nginx with a self-signed HTTPS certificate, reachable only from private networks
- adds firewall rules that allow ports 80 and 443 only from private networks (skip with `--no-firewall`)

At the end it prints the setup code:

```
==> NetUSBFlash 0.1.0-alpha.1 installed.
Open https://netusbflash.local (or https://<IP address>) in your browser.
Setup code: 7KQ4-M2XD-9PRT
Warning: USB device mode was enabled. Please reboot once: sudo reboot
```

Reboot once so USB device mode becomes active:

```bash
sudo reboot
```

## Step 3: Run the setup wizard

Open `https://netusbflash.local` (or `https://<IP address>`) in your browser.
Your browser warns about the self-signed certificate; check that the address is
your Pi and continue.

| Step | What to do |
| --- | --- |
| Language and code | Choose English or Deutsch and enter the setup code. Lost it? `sudo netusbflash-cli setup show-code` |
| Administrator | Username, email address and a password with at least 12 characters. |
| System | Device name (hostname) and time zone. |
| USB stick | Size, file system (exFAT or FAT32), volume label, sync mode, wait time. This formats the emulated stick. |
| Upload target | Your first target, with **Test connection**. You can skip this and add targets later. |
| Email | SMTP server for notifications, with a test email. Optional. |
| Finish | Click **Finish setup**, then log in. |

You can leave the wizard at any time; it continues at the last step.

### Choosing the USB stick settings

- **File system:** exFAT supports files larger than 4 GB (long multitrack
  recordings). Choose FAT32 if your console does not recognise exFAT.
- **Size:** the image is created as a sparse file and only uses SD card space as
  it fills up. Leave room for the upload queue: new recordings are copied to
  the SD card before they are uploaded.
- **Sync mode:**
    - *Disconnect briefly* (recommended): after the console has stopped writing,
      the stick is disconnected for a few seconds while new files are copied.
      Do not start a new recording during that moment.
    - *Stay connected* (experimental): the stick is read while it stays
      connected. Files written during the check can be incomplete; they are
      picked up again on the next check.
- **Wait after last write:** how long the console must not write before files
  are picked up. 30 seconds works for most devices; increase it if a recorder
  pauses while writing.

## Step 4: Connect the console

Connect the Pi's USB data port (Zero 2 W: "USB"; Pi 4/5: USB-C via the
splitter) to the console's USB port for recording. The dashboard shows
**Connected to host** once the console has detected the stick.

Some consoles want to format the stick themselves. That is fine; NetUSBFlash
works with whatever FAT32 or exFAT file system is on it.

Record a short test, stop the recording, and watch the dashboard: after the
wait time the file appears under **Recent file events** and is uploaded.

## Step 5: Add upload targets

Go to **Targets → Add target** (role Manager or Administrator), pick the
protocol, fill in the fields, click **Test connection**, then save. Every new or
changed recording is uploaded to every enabled target.

| Protocol | Server / URL | Folder | Notes |
| --- | --- | --- | --- |
| SMB / CIFS | `nas.local` | `share/folder` | Use a dedicated NAS user. Domain only for Active Directory. |
| WebDAV / Nextcloud | `https://cloud.example.com/remote.php/dav/files/<user>/` | `Recordings` | Server type Nextcloud. Use an app password (Nextcloud: Settings → Security). |
| FTP | `ftp.example.com` | `/upload` | Unencrypted, local network only. |
| FTPS | `ftp.example.com` | `/upload` | Explicit TLS (port 21) or implicit TLS (port 990). Keep certificate checking on. |
| SFTP / SSHFS | `server.example.com` | `/home/user/recordings` | Prefer **SSH key**: generate the key, add the shown public key to `~/.ssh/authorized_keys` on the server. |
| SCP | `server.example.com` | `recordings` | Copy only. Password login needs `sshpass` (installed); key login is recommended. |
| Local folder | – | `/media/usbdisk/recordings` | A disk attached to the Pi. |

**Subfolder per upload** sorts uploads into folders, e.g. `{date}` →
`2026-10-26/`. Placeholders: `{date}`, `{year}`, `{month}`, `{day}`, `{time}`,
`{hostname}`.

Failed uploads are retried automatically (after 1, 2, 4 … minutes, at most 10
times). Under **Uploads** you can retry or discard them.

## Step 6: Email notifications

Under **Notifications** (role Manager or Administrator):

1. Enter the SMTP server: host, port 587 with STARTTLS (most providers) or 465
   with SSL/TLS, username, password (often an app password) and sender address.
   Save and send a test email.
2. Add a rule: choose the events (new, changed, deleted, uploaded, upload
   failed), an optional file pattern such as `*.wav`, the recipients, and
   *immediately* or *summary every N minutes*.

Emails are written in the recipient's language if the address belongs to a
user, otherwise in English. Failed emails are retried automatically.

## Step 7: Users and roles

Administrators add users under **Users**. A temporary password is shown once;
the user must change it at the first login.

| Role | May |
| --- | --- |
| Viewer | see dashboard, files, uploads and logs |
| Operator | + start a check, connect/disconnect the stick, retry uploads |
| Manager | + manage targets, USB settings and notifications |
| Administrator | + users, recreating the USB image, system settings |

After five wrong passwords an account is locked for 15 minutes; administrators
can unlock it earlier.

## Troubleshooting

| Problem | What to do |
| --- | --- |
| `netusbflash.local` does not open | Use the IP address from your router. Some Windows and Android devices do not resolve `.local` names. |
| "USB device mode is not available" | Reboot once after installing. Check that `config.txt` contains `dtoverlay=dwc2,dr_mode=peripheral` and that the model supports device mode (see *Before you start*). |
| Dashboard shows "Ready, no host" | Check the cable (Zero 2 W: the port labelled "USB", not "PWR"; some cables are charge-only). Try another USB port on the console. |
| The console does not see files after a check | Use the sync mode *Disconnect briefly*; with *Stay connected*, the console may cache the old directory. |
| Files are not picked up | The console may still be writing; increase *Wait after last write*. Check include/exclude patterns. Use **Check for new files** on the USB stick page. |
| Connection test fails | Check address, port, user, password; for FTPS/WebDAV the certificate; for SFTP/SCP that the public key is on the server. |
| No emails | Send a test email; the error is shown under *Recent emails*. |
| Setup code lost | `sudo netusbflash-cli setup show-code` |
| Administrator password lost | `sudo netusbflash-cli user reset-password <username>` |
| Start over | **System → Run setup again**, or `sudo netusbflash-cli setup reset` |

Logs on the command line:

```bash
sudo journalctl -u netusbflash -f        # service log
sudo tail -f /var/log/nginx/error.log    # web server errors
```

## Updating

```bash
cd ~/netusbflash
git pull
sudo ./packaging/install.sh --upgrade
```

Settings, users, targets and the USB image are kept. The stick is disconnected
from the console for a few seconds while the service restarts.

## Uninstalling

```bash
sudo ./packaging/install.sh --uninstall           # keeps /etc/netusbflash and /var/lib/netusbflash
sudo ./packaging/install.sh --uninstall --purge   # also deletes settings, users and the USB image
```

Files already uploaded to your targets are never deleted.

## Files and folders on the Pi

| Path | Content |
| --- | --- |
| `/opt/netusbflash` | program files |
| `/etc/netusbflash` | encryption key, HTTPS certificate, setup code, nginx and firewall snippets |
| `/var/lib/netusbflash/state.db` | settings, users, queue, logs (SQLite) |
| `/var/lib/netusbflash/usb.img` | the emulated USB stick |
| `/var/lib/netusbflash/spool` | copies of recordings waiting for upload |
| `/var/lib/netusbflash/ssh` | SSH key and known hosts for SFTP/SCP targets |

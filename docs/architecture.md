# Architecture

NetUSBFlash consists of two programs on the Pi:

| Part | Language | Runs as | Job |
| --- | --- | --- | --- |
| Service (`daemon/`) | Python 3 (standard library + `cryptography`) | root, systemd unit `netusbflash` | USB gadget, recording detection, uploads, email, JSON API |
| Web interface (`web/`) | PHP 8, HTML, Bootstrap 5, plain JavaScript | `www-data` via nginx + PHP-FPM | forms and pages; no direct system access |

```
Browser ──HTTPS (LAN only)──▶ nginx ──▶ PHP-FPM (www-data)
                                           │ JSON over Unix socket
                                           ▼  /run/netusbflash/api.sock (group netusbflash)
                                     Python service (root)
             ┌──────────────┬──────────────┼──────────────┬──────────────┐
          gadget         monitor        uploader         mailer         SQLite
       (configfs)    (detect files)   (rclone/scp)       (SMTP)       state.db
             │
     USB host (mixer)
```

## Why two languages

The web interface was requested in PHP/HTML/JavaScript. The system part needs
root privileges (configfs, loop mounts, hostname), long-running worker threads
and robust process handling, which Python's standard library covers well and
which is preinstalled on Raspberry Pi OS. Keeping PHP unprivileged means a bug
in the web interface cannot run commands as root; every action goes through the
API, which validates input and checks the user's role.

## Components (daemon/netusbflash)

| Module | Responsibility |
| --- | --- |
| `service.py` | entry point; wires all components (`Context`), starts workers and the API server |
| `api.py` | HTTP server on a Unix socket, routing, role checks, error format |
| `handlers.py` | all API endpoints |
| `auth.py` | users, scrypt password hashes, sessions, lockout, roles |
| `setup.py` | setup wizard state and the one-time setup code |
| `gadget.py` | USB mass-storage gadget via configfs; disk image creation; simulated gadget for development |
| `monitor.py` | idle detection, scanning the stick, file index, queueing uploads |
| `uploader.py` | upload queue with retries and backoff |
| `transports.py` | protocol backends: rclone (SMB, WebDAV, FTP/FTPS, SFTP/SSHFS), OpenSSH scp, local copy |
| `mailer.py` | notification rules, digests, SMTP client, mail queue |
| `crypto.py` | Fernet encryption for stored passwords |
| `db.py` | SQLite schema and helpers |
| `cli.py` | `netusbflash-cli` recovery tool |

## How a recording travels

1. The console writes to the disk image `usb.img` through the USB gadget; the
   file's modification time changes.
2. The monitor waits until the image has not changed for `idle_seconds`.
3. In sync mode *detach*, it unbinds the gadget from the USB controller (the
   console sees the stick removed), mounts the image (loop device, offset of the
   first partition), and compares the files with the file index in SQLite.
   In mode *live*, it mounts read-only without detaching.
4. New and changed files are copied to `spool/<event id>/` and one upload row
   per enabled target is queued; deleted files are recorded as events.
5. The gadget is bound again; the console sees the stick again.
6. The uploader sends each queued file with rclone or scp. On success the spool
   copy is removed once all targets are done; on failure it retries with
   exponential backoff (max. 10 tries).
7. Notification rules turn events into email, immediately or as a digest.

The first scan after a new image only records a baseline; it neither uploads
nor sends email.

## Security model

- Web UI only from private address ranges (nginx `allow`/`deny` + nftables table `inet netusbflash`).
- HTTPS with a self-signed certificate generated at install time.
- PHP sessions: `HttpOnly`, `Secure`, `SameSite=Strict`; CSRF token on every form; strict Content Security Policy (no inline scripts or styles).
- API: socket mode 0660, group `netusbflash`; session tokens stored as SHA-256 hashes; idle timeout 30 min, max 12 h.
- Passwords: scrypt (n=2^14, r=8, p=1); lockout after 5 failures for 15 minutes.
- Stored credentials (targets, SMTP) are encrypted with Fernet; the key is in `/etc/netusbflash/secret.key` (root only). rclone configs are written per transfer to `/run` with mode 0600 and removed afterwards.
- External commands are always started with an argument list, never through a shell.
- Setup wizard requires the one-time code from the installer; the code is deleted when setup is finished.

Known gaps (alpha): no host key pinning for rclone SFTP targets; scrypt instead
of Argon2id (no extra dependency); no rate limiting of the API beyond login and
setup code.

## Data model

See `daemon/netusbflash/db.py`. Main tables: `settings` (JSON values), `users`,
`sessions`, `targets`, `file_index`, `file_events`, `uploads`, `notify_rules`,
`notify_items`, `mail_queue`, `events` (log), `audit_log`.

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

## Web interface

Every page is delivered as an HTML skeleton by PHP (texts, form fields, table
templates). The page script in `web/public/assets/js/pages/` then loads the
data via AJAX from `/ajax/api/<path>`, a thin gateway (`web/pages/ajax_api.php`)
that forwards allowed paths to the service with the user's session token and
translates error messages. Forms are saved the same way. While any request
runs, a loading spinner covers the page. The setup wizard uses its own
endpoints under `/setup/api/` because it works before anyone is logged in.
Shared helpers (requests, spinner, forms, lists, notices) are in
`web/public/assets/js/app.js`.

### File manager

The **Files** page shows [FileGator](https://filegator.io) (MIT, PHP + Vue)
in a frame under `/fm/`. FileGator is installed to `/opt/netusbflash/filegator`
and started through our own entry point (`web/filegator/entry.php`), so its
program folder stays read-only. There is no second login: nginx checks every
`/fm/` request with `auth_request` against `web/auth/filemanager.php`, which
validates the NetUSBFlash session and returns the user's name, role and
language as headers; nginx passes them to FileGator as `NUF_USER`, `NUF_ROLE`,
`NUF_LOCALE`, and the auth adapter `web/filegator/NetUsbFlashAuth.php` maps
them to permissions (read and download for everyone; write, upload and zip
for managers and administrators, and only while the folder is writable).

What FileGator sees is decided by the service (`browser.py`): it loop-mounts
the USB image at `/srv/netusbflash/usb-stick` — read-only with group
`netusbflash` in *view* mode, writable in *edit* mode, which first disconnects
the USB host (a FAT/exFAT file system must never be written by two systems at
once). The monitor unmounts the view while it scans, so the view is refreshed
after each check. Edit mode ends after 30 minutes; afterwards the host is
reconnected and the stick is scanned.

### Mail templates

Rules store a subject and an HTML body. The body is edited with Quill
(BSD-3-Clause, bundled) and sanitised by the service (`htmlsafe.py`: allow-list
of tags, attributes and CSS properties; Quill's alignment and indent classes
become inline styles). Placeholders (`{{name}}`) are replaced when a mail is
composed; values are HTML-escaped in the HTML part. Mails are multipart
(plain text + HTML). The notifications page is the only page whose CSP allows
inline styles, because the editor needs them; scripts stay external
everywhere. The preview is shown in a sandboxed `iframe` without scripts.

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
| `converter.py` | conversion rules and the ffmpeg worker that converts recordings (FLAC, MP3, AAC) before the upload |
| `transports.py` | protocol backends: rclone (SMB, WebDAV, FTP/FTPS, SFTP/SSHFS), OpenSSH scp, local copy |
| `mailer.py` | notification rules, templates and placeholders, digests, SMTP client, mail queue |
| `htmlsafe.py` | allow-list HTML sanitiser for mail templates |
| `browser.py` | file manager mount (off / view / edit) and edit timeout |
| `updater.py` | release check on GitHub, software and OS updates as transient systemd units |
| `backup.py` | configuration export/restore, passphrase encryption, scheduled upload |
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
   If a conversion rule matches the file type, the event is marked for
   conversion and the uploads point at the converted file. The converter
   thread runs ffmpeg on the spool copy (after the stick is back with the
   console) and writes `spool/<event id>/converted/<name>.<flac|mp3|m4a>`;
   the uploader holds those uploads until then. If ffmpeg fails, the original
   is uploaded instead (or, with "also upload the original", the converted
   uploads are marked failed and a retry converts again).
6. The uploader sends each queued file with rclone or scp. On success the spool
   copy is removed once all targets are done; on failure it retries with
   exponential backoff (max. 10 tries).
7. Notification rules turn events into email, immediately or as a digest.

The first scan after a new image only records a baseline; it neither uploads
nor sends email.

## Security model

- Web UI only from private address ranges (nginx `allow`/`deny` + nftables table `inet netusbflash`).
- HTTPS with a self-signed certificate generated at install time.
- PHP sessions: `HttpOnly`, `Secure`, `SameSite=Strict`; CSRF token on every form; strict Content Security Policy (no inline scripts; inline styles only on the notifications page for the mail editor).
- API: socket mode 0660, group `netusbflash`; session tokens stored as SHA-256 hashes; idle timeout 30 min, max 12 h.
- Passwords: scrypt (n=2^14, r=8, p=1); lockout after 5 failures for 15 minutes.
- Stored credentials (targets, SMTP) are encrypted with Fernet; the key is in `/etc/netusbflash/secret.key` (root only). rclone configs are written per transfer to `/run` with mode 0600 and removed afterwards.
- External commands are always started with an argument list, never through a shell.
- Setup wizard requires the one-time code from the installer; the code is deleted when setup is finished.
- File manager: every request is authorised by nginx `auth_request` against the NetUSBFlash session; FileGator runs as `www-data` and can only write while the service has mounted the image writable (edit mode, managers only). Symlinks are not followed.
- Updates: release archives are verified against the published SHA-256 file and unpacked without links or paths outside the work folder. The checksum comes from the same GitHub release, so it protects against damaged downloads, not against a compromised repository (signed releases are on the roadmap).
- Backups: passwords are only included when a passphrase is given; they are then encrypted with a key derived from it (scrypt + Fernet). Without the passphrase they cannot be read.

Known gaps (alpha): no host key pinning for rclone SFTP targets; scrypt instead
of Argon2id (no extra dependency); no rate limiting of the API beyond login and
setup code.

## Data model

See `daemon/netusbflash/db.py`. Main tables: `settings` (JSON values), `users`,
`sessions`, `targets`, `file_index`, `file_events`, `uploads`, `notify_rules`,
`notify_items`, `mail_queue`, `events` (log), `audit_log`.

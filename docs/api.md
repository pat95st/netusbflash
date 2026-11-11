# Local API

The service listens on the Unix socket `/run/netusbflash/api.sock` (mode 0660,
group `netusbflash`). It speaks JSON over HTTP/1.1; all paths start with
`/api/v1`. The PHP web interface is its only client.

## Authentication

- `POST /api/v1/auth/login` with `{"username", "password"}` returns `{"token", "user"}`.
- Send the token in the `X-Session-Token` header with every later request.
- Setup endpoints need the one-time setup code in the `X-Setup-Code` header and
  only work until the setup is finished.
- Access levels: `public`, `setup`, or the minimum role (`viewer` < `operator` < `manager` < `admin`).

## Errors

Errors return a status code and `{"error": "<code>", "message": "…", "fields": {"<field>": "<code>"}}`.
Validation errors use status 422 and the code `validation`; field codes are
`required`, `invalid`, `too_long`, `too_short`, `out_of_range`, `taken`,
`wrong_password`, `same_password`, `requires_detach`.

Example:

```bash
sudo curl -s --unix-socket /run/netusbflash/api.sock http://localhost/api/v1/health
```

## Endpoints

| Method | Path | Access |
| --- | --- | --- |
| GET | `/api/v1/health` | public |
| GET | `/api/v1/setup/status` | public |
| POST | `/api/v1/setup/verify` | setup |
| POST | `/api/v1/setup/step` | setup |
| POST | `/api/v1/setup/admin` | setup |
| GET | `/api/v1/setup/timezones` | setup |
| POST | `/api/v1/setup/system` | setup |
| GET | `/api/v1/setup/usb` | setup |
| POST | `/api/v1/setup/usb` | setup |
| POST | `/api/v1/setup/target` | setup |
| POST | `/api/v1/setup/smtp` | setup |
| POST | `/api/v1/setup/finish` | setup |
| POST | `/api/v1/auth/login` | public |
| POST | `/api/v1/auth/logout` | viewer |
| GET | `/api/v1/me` | viewer |
| PUT | `/api/v1/me` | viewer |
| POST | `/api/v1/me/password` | viewer |
| GET | `/api/v1/users` | admin |
| POST | `/api/v1/users` | admin |
| PUT | `/api/v1/users/{id}` | admin |
| POST | `/api/v1/users/{id}/reset-password` | admin |
| POST | `/api/v1/users/{id}/unlock` | admin |
| DELETE | `/api/v1/users/{id}` | admin |
| GET | `/api/v1/status` | viewer |
| GET | `/api/v1/usb` | viewer |
| PUT | `/api/v1/usb` | manager |
| POST | `/api/v1/usb/attach` | operator |
| POST | `/api/v1/usb/detach` | operator |
| POST | `/api/v1/usb/sync` | operator |
| POST | `/api/v1/usb/image` | admin |
| GET | `/api/v1/files` | viewer |
| GET | `/api/v1/file-events` | viewer |
| GET | `/api/v1/targets` | viewer |
| POST | `/api/v1/targets` | manager |
| POST | `/api/v1/targets/test` | manager |
| GET | `/api/v1/targets/{id}` | viewer |
| PUT | `/api/v1/targets/{id}` | manager |
| DELETE | `/api/v1/targets/{id}` | manager |
| POST | `/api/v1/targets/{id}/test` | manager |
| GET | `/api/v1/uploads` | viewer |
| POST | `/api/v1/uploads/retry-failed` | operator |
| POST | `/api/v1/uploads/{id}/retry` | operator |
| POST | `/api/v1/uploads/{id}/discard` | manager |
| GET | `/api/v1/smtp` | manager |
| PUT | `/api/v1/smtp` | manager |
| POST | `/api/v1/smtp/test` | manager |
| GET | `/api/v1/rules` | manager |
| POST | `/api/v1/rules/preview` | manager |
| POST | `/api/v1/rules` | manager |
| PUT | `/api/v1/rules/{id}` | manager |
| DELETE | `/api/v1/rules/{id}` | manager |
| GET | `/api/v1/mail-queue` | manager |
| GET | `/api/v1/events` | viewer |
| GET | `/api/v1/audit` | admin |
| GET | `/api/v1/system` | admin |
| PUT | `/api/v1/system` | admin |
| POST | `/api/v1/system/reboot` | admin |
| POST | `/api/v1/system/poweroff` | admin |
| POST | `/api/v1/system/setup-reset` | admin |
| GET | `/api/v1/system/ssh-key` | manager |
| POST | `/api/v1/system/ssh-key` | manager |
| GET | `/api/v1/browser` | viewer |
| POST | `/api/v1/browser` | viewer |
| POST | `/api/v1/browser/refresh` | viewer |
| GET | `/api/v1/update` | admin |
| PUT | `/api/v1/update` | admin |
| POST | `/api/v1/update/check` | admin |
| POST | `/api/v1/update/software` | admin |
| POST | `/api/v1/update/os-check` | admin |
| POST | `/api/v1/update/os` | admin |
| GET | `/api/v1/conversion` | viewer |
| PUT | `/api/v1/conversion` | manager |
| GET | `/api/v1/backup` | admin |
| PUT | `/api/v1/backup` | admin |
| POST | `/api/v1/backup/run` | admin |
| POST | `/api/v1/backup/export` | admin |
| POST | `/api/v1/backup/restore` | admin |

## Notes on newer endpoints

- `POST /browser` with `{"mode": "off" | "view" | "edit"}` switches the file
  manager's view of the USB image. `view` mounts it read-only at
  `/srv/netusbflash/usb-stick`; `edit` (manager or higher) disconnects the host
  and mounts it writable until the mode is left or the timeout (30 minutes)
  ends.
- Notification rules accept `subject_template` (text, max. 250 characters) and
  `body_template` (HTML, sanitised on save). Empty means the built-in text.
  `GET /rules` lists the available placeholders and the default texts;
  `POST /rules/preview` renders a rule with example files and, with
  `send_to`, sends it as a test mail.
- `POST /update/software` and `POST /update/os` start a transient systemd
  unit; its output is returned as `log` by `GET /update`.
- `POST /backup/export` with an optional `passphrase` returns
  `{"filename", "backup"}`. `POST /backup/restore` with `{"backup", "passphrase"}`
  replaces settings, targets, rules and users and ends all sessions. Error
  codes: `invalid_backup`, `backup_too_new`, `backup_without_admin`,
  `passphrase_required`, `wrong_passphrase`.
- `PUT /conversion` takes `{"enabled": bool, "rules": [...]}`. Each rule has
  `enabled`, `extensions` (list or comma-separated text, e.g. `"wav, aiff"`),
  `format` (`flac`, `mp3`, `aac`), `bitrate` (kbit/s, MP3 CBR and AAC),
  `mp3_mode` (`cbr`, `vbr`), `vbr_quality` (0–9), `flac_level` (0–8),
  `bit_depth` (0 = keep, 16, 24; FLAC only), `sample_rate` (0 = keep, or Hz),
  `channels` (0 = keep, 1, 2) and `keep_original`. The first enabled rule whose
  extensions match is used; an extension may appear in only one enabled rule.
  Field errors are reported as `rules.<index>.<field>`. `GET /conversion`
  also returns the allowed values (`choices`), whether ffmpeg is installed
  and the conversion queue.

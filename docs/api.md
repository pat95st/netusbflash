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

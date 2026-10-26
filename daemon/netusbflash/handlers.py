"""API endpoint handlers."""

from __future__ import annotations

import json
import re
import shutil
import time
from typing import TYPE_CHECKING, Any

from . import __version__, system
from .api import ApiError, Request, Router
from .auth import LOCALES, ROLES, AuthError, generate_password, public_user, verify_password
from .gadget import DEFAULT_USB, FILESYSTEMS, SYNC_MODES, GadgetError
from .mailer import DEFAULT_SMTP, EVENT_TYPES, SECURITY_MODES, MailError
from .setup import STEPS
from .system import CommandError
from .transports import DEFAULT_OPTIONS, PROTOCOLS, TransferError, make_transport
from .validate import (BWLIMIT_RE, HEX16_RE, HOST_RE, HOSTNAME_RE, LABEL_RE, SAFE_TEXT_RE,
                       TIMEZONE_RE, USERNAME_RE, ValidationError, Validator)

if TYPE_CHECKING:
    from .service import Context

SERIAL_RE = re.compile(r"^[A-Za-z0-9]{0,32}$")
URL_RE = re.compile(r"^https?://[^\s]{1,500}$")
MIN_IMAGE_MB = 64


# Helpers ---------------------------------------------------------------------

def _limit(req: Request, default: int = 100, maximum: int = 1000) -> int:
    try:
        return max(1, min(int(req.q("limit", str(default))), maximum))
    except ValueError:
        return default


def target_public(ctx: "Context", row: dict[str, Any]) -> dict[str, Any]:
    view = ctx.target_view(row)
    counts = {r["status"]: r["n"] for r in ctx.db.all(
        "SELECT status, COUNT(*) AS n FROM uploads WHERE target_id = ? GROUP BY status", (row["id"],))}
    return {
        "id": row["id"], "name": row["name"], "protocol": row["protocol"], "host": row["host"],
        "port": row["port"], "path": row["path"], "username": row["username"],
        "has_password": bool(row["secret"]), "options": view["options"], "enabled": bool(row["enabled"]),
        "uploads": {"pending": counts.get("pending", 0), "done": counts.get("done", 0),
                    "failed": counts.get("failed", 0)},
    }


def parse_target(body: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    """Validate target fields. Returns (fields, password or None to keep)."""
    v = Validator(body)
    name = v.string("name", required=True, max_len=64)
    protocol = v.choice("protocol", PROTOCOLS)
    if protocol == "webdav":
        host = v.string("host", required=True, max_len=500, pattern=URL_RE)
    elif protocol == "local":
        host = ""
    else:
        host = v.string("host", required=True, max_len=253, pattern=HOST_RE)
    port = v.integer("port", minimum=1, maximum=65535, default=None)
    path = v.remote_path("path")
    if protocol == "local" and not path.startswith("/"):
        v.errors["path"] = "invalid"
    if protocol == "smb" and not path.strip("/"):
        v.errors["path"] = "required"
    username = v.string("username", max_len=128)
    enabled = v.boolean("enabled", True)
    raw_password = body.get("password")
    password: str | None = None
    if isinstance(raw_password, str) and raw_password != "":
        if len(raw_password) > 256 or "\n" in raw_password:
            v.errors["password"] = "invalid"
        password = raw_password
    elif body.get("clear_password"):
        password = ""
    ov = Validator(body.get("options") or {})
    options = {
        "domain": ov.string("domain", max_len=64),
        "vendor": ov.choice("vendor", ("other", "nextcloud", "owncloud"), "other"),
        "tls_mode": ov.choice("tls_mode", ("explicit", "implicit"), "explicit"),
        "insecure_tls": ov.boolean("insecure_tls", False),
        "auth": ov.choice("auth", ("password", "key"), "password"),
        "subfolder": ov.string("subfolder", max_len=128, default=DEFAULT_OPTIONS["subfolder"]),
        "keep_structure": ov.boolean("keep_structure", True),
        "bwlimit": ov.string("bwlimit", max_len=8, pattern=BWLIMIT_RE),
    }
    if ".." in options["subfolder"].split("/"):
        ov.errors["subfolder"] = "invalid"
    v.errors.update({f"options.{k}": e for k, e in ov.errors.items()})
    v.raise_if_errors()
    fields = {"name": name, "protocol": protocol, "host": host, "port": port, "path": path,
              "username": username, "options": json.dumps(options), "enabled": int(enabled)}
    return fields, password


def parse_usb(body: dict[str, Any], current: dict[str, Any], max_mb: int) -> dict[str, Any]:
    merged = {**current, **{k: body[k] for k in body if k in DEFAULT_USB}}
    v = Validator(merged)
    v.boolean("enabled", True)
    v.integer("size_mb", minimum=MIN_IMAGE_MB, maximum=max(max_mb, MIN_IMAGE_MB), required=True)
    v.choice("filesystem", FILESYSTEMS)
    label = str(merged.get("label", "")).strip().upper()
    merged["label"] = label
    v.data = merged
    v.string("label", required=True, max_len=11, pattern=LABEL_RE)
    v.boolean("partition_table", True)
    v.boolean("removable", True)
    v.boolean("read_only", False)
    v.boolean("cdrom", False)
    v.string("vendor_id", required=True, pattern=HEX16_RE)
    v.string("product_id", required=True, pattern=HEX16_RE)
    v.string("manufacturer", required=True, max_len=32, pattern=SAFE_TEXT_RE)
    v.string("product", required=True, max_len=32, pattern=SAFE_TEXT_RE)
    v.string("serial", max_len=32, pattern=SERIAL_RE)
    v.integer("max_power_ma", minimum=2, maximum=500, default=100)
    v.choice("sync_mode", SYNC_MODES)
    v.integer("idle_seconds", minimum=5, maximum=3600, default=30)
    v.boolean("delete_after_upload", False)
    v.string("include", max_len=256, default="*")
    v.string("exclude", max_len=256)
    if v.clean.get("delete_after_upload") and v.clean.get("sync_mode") != "detach":
        v.errors["delete_after_upload"] = "requires_detach"
    if v.clean.get("read_only") and v.clean.get("delete_after_upload"):
        v.errors["delete_after_upload"] = "invalid"
    v.raise_if_errors()
    return {k: v.clean.get(k, merged[k]) for k in DEFAULT_USB}


def max_image_mb(ctx: "Context") -> int:
    free = shutil.disk_usage(ctx.paths.lib).free
    existing = ctx.paths.image.stat().st_size if ctx.paths.image.exists() else 0
    # Keep 1 GiB for the system and the upload spool.
    return max(int((free + existing - 1024**3) / 1024**2), 0)


def smtp_public(cfg: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in cfg.items() if k != "password"}
    out["has_password"] = bool(cfg.get("password"))
    return out


def parse_smtp(ctx: "Context", body: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    v = Validator(body)
    cfg = {
        "host": v.string("host", required=True, max_len=253, pattern=HOST_RE),
        "port": v.integer("port", minimum=1, maximum=65535, default=587),
        "security": v.choice("security", SECURITY_MODES, "starttls"),
        "username": v.string("username", max_len=254),
        "sender": v.email("sender", required=True),
        "sender_name": v.string("sender_name", max_len=64, default="NetUSBFlash"),
        "verify_tls": v.boolean("verify_tls", True),
        "password": current.get("password", ""),
    }
    pw = body.get("password")
    if isinstance(pw, str) and pw:
        cfg["password"] = ctx.secrets.encrypt(pw)
    elif body.get("clear_password"):
        cfg["password"] = ""
    v.raise_if_errors()
    return cfg


def parse_rule(body: dict[str, Any]) -> dict[str, Any]:
    v = Validator(body)
    name = v.string("name", required=True, max_len=64)
    events = body.get("events") or []
    if isinstance(events, str):
        events = [e for e in events.split(",") if e]
    if not events or any(e not in EVENT_TYPES for e in events):
        v.errors["events"] = "invalid"
    pattern = v.string("pattern", max_len=256, default="*") or "*"
    recipients = v.emails("recipients", required=True)
    mode = v.choice("mode", ("instant", "digest"), "instant")
    minutes = v.integer("digest_minutes", minimum=5, maximum=10080, default=60)
    enabled = v.boolean("enabled", True)
    v.raise_if_errors()
    return {"name": name, "events": ",".join(e for e in EVENT_TYPES if e in events), "pattern": pattern,
            "recipients": ",".join(recipients), "mode": mode, "digest_minutes": minutes,
            "enabled": int(enabled)}


def rule_public(row: dict[str, Any]) -> dict[str, Any]:
    return {**row, "events": row["events"].split(","), "recipients": row["recipients"].split(","),
            "enabled": bool(row["enabled"])}


def run_target_test(ctx: "Context", fields: dict[str, Any], password: str) -> dict[str, Any]:
    view = ctx.target_view({**fields, "options": fields["options"]})
    transport = make_transport(view, password, ctx.paths)
    started = time.time()
    try:
        steps = transport.test()
    except (TransferError, CommandError, OSError) as exc:
        return {"ok": False, "error": str(exc), "steps": [], "duration": round(time.time() - started, 1)}
    return {"ok": True, "steps": steps, "duration": round(time.time() - started, 1)}


def apply_gadget(ctx: "Context") -> str:
    cfg = ctx.usb_settings()
    try:
        if cfg["enabled"]:
            ctx.gadget.apply(cfg)
        else:
            ctx.gadget.teardown()
    except (GadgetError, OSError, CommandError) as exc:
        ctx.db.log("error", "usb", f"Could not apply USB settings: {exc}")
        return str(exc)
    return ""


def create_image(ctx: "Context", cfg: dict[str, Any]) -> None:
    with ctx.monitor.sync_lock:
        try:
            ctx.gadget.create_image(cfg)
        except (GadgetError, CommandError, OSError) as exc:
            raise ApiError(500, "image_failed", str(exc)) from exc
        ctx.db.run("DELETE FROM file_index")
        ctx.db.set_setting("index_initialized", True)
        ctx.monitor.seen_write = ctx.gadget.last_write()
        ctx.db.log("info", "usb", f"Created a new {cfg['size_mb']} MB {cfg['filesystem']} image")


# Handlers --------------------------------------------------------------------

def register(router: Router, ctx: "Context") -> None:
    db = ctx.db
    r = router.add

    # Health and setup ------------------------------------------------------

    def health(req: Request):
        return {"ok": True, "version": __version__}

    def setup_status(req: Request):
        return {"completed": ctx.setup.completed(), "step": ctx.setup.step(), "steps": list(STEPS),
                "has_admin": ctx.auth.active_admins() > 0, "simulated": ctx.simulated}

    def setup_verify(req: Request):
        return {"ok": True, "step": ctx.setup.step()}

    def setup_goto(req: Request):
        step = req.body.get("step")
        if step not in STEPS or STEPS.index(step) > STEPS.index(ctx.setup.step()):
            raise ApiError(400, "invalid_step")
        ctx.setup.set_step(step)
        return {"step": step}

    def setup_admin(req: Request):
        v = Validator(req.body)
        username = v.string("username", required=True, max_len=32, pattern=USERNAME_RE)
        email = v.email("email")
        password = v.password("password")
        locale = v.choice("locale", LOCALES, "en")
        v.raise_if_errors()
        existing = ctx.auth.find_user(username)
        if existing:
            db.run("UPDATE users SET email = ?, role = 'admin', locale = ?, disabled = 0 WHERE id = ?",
                   (email, locale, existing["id"]))
            ctx.auth.set_password(existing["id"], password)
        else:
            ctx.auth.create_user(username, email, "admin", locale, password)
        db.set_setting("default_locale", locale)
        db.audit(None, "setup.admin", username)
        return {"step": ctx.setup.advance("admin")}

    def setup_timezones(req: Request):
        return {"timezones": system.list_timezones(), "current": system.timezone(),
                "hostname": system.hostname()}

    def setup_system(req: Request):
        apply_system_settings(req.body)
        return {"step": ctx.setup.advance("system")}

    def apply_system_settings(body: dict[str, Any]) -> dict[str, Any]:
        v = Validator(body)
        hostname = v.string("hostname", required=True, max_len=63, pattern=HOSTNAME_RE)
        tz = v.string("timezone", required=True, max_len=64, pattern=TIMEZONE_RE)
        v.raise_if_errors()
        if tz not in system.list_timezones():
            raise ValidationError({"timezone": "invalid"})
        if not ctx.simulated:
            try:
                if hostname != system.hostname():
                    system.set_hostname(hostname)
                if tz != system.timezone():
                    system.set_timezone(tz)
            except CommandError as exc:
                raise ApiError(500, "system_failed", str(exc)) from exc
        db.set_setting("system", {"hostname": hostname, "timezone": tz})
        return {"hostname": hostname, "timezone": tz}

    def setup_usb_info(req: Request):
        ok, reason = ctx.gadget.available()
        return {"settings": ctx.usb_settings(), "max_size_mb": max_image_mb(ctx), "available": ok,
                "unavailable_reason": reason, "model": system.pi_model()}

    def setup_usb(req: Request):
        cfg = parse_usb(req.body, ctx.usb_settings(), max_image_mb(ctx))
        db.set_setting("usb", cfg)
        create_image(ctx, cfg)
        return {"step": ctx.setup.advance("usb"), "settings": cfg}

    def setup_target(req: Request):
        if req.body.get("skip"):
            return {"step": ctx.setup.advance("target")}
        fields, password = parse_target(req.body)
        if req.body.get("test_only"):
            return run_target_test(ctx, fields, password or "")
        now = time.time()
        db.run("INSERT INTO targets(name, protocol, host, port, path, username, secret, options, enabled, "
               "created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
               (fields["name"], fields["protocol"], fields["host"], fields["port"], fields["path"],
                fields["username"], ctx.secrets.encrypt(password or ""), fields["options"],
                fields["enabled"], now, now))
        return {"step": ctx.setup.advance("target")}

    def setup_smtp(req: Request):
        if req.body.get("skip"):
            return {"step": ctx.setup.advance("smtp")}
        cfg = parse_smtp(ctx, req.body, ctx.mailer.settings())
        to = req.body.get("test_to")
        if to:
            try:
                ctx.mailer.send_test(str(to), req.body.get("locale", "en"), cfg)
            except MailError as exc:
                return {"ok": False, "error": str(exc)}
            if req.body.get("test_only"):
                return {"ok": True}
        db.set_setting("smtp", cfg)
        return {"ok": True, "step": ctx.setup.advance("smtp")}

    def setup_finish(req: Request):
        if ctx.auth.active_admins() == 0:
            raise ApiError(409, "admin_missing")
        ctx.setup.finish()
        error = apply_gadget(ctx) if ctx.gadget.image_exists() else ""
        db.audit(None, "setup.finish")
        db.log("info", "system", "Setup wizard completed")
        return {"ok": True, "gadget_error": error}

    r("GET", "/health", health, "public")
    r("GET", "/setup/status", setup_status, "public")
    r("POST", "/setup/verify", setup_verify, "setup")
    r("POST", "/setup/step", setup_goto, "setup")
    r("POST", "/setup/admin", setup_admin, "setup")
    r("GET", "/setup/timezones", setup_timezones, "setup")
    r("POST", "/setup/system", setup_system, "setup")
    r("GET", "/setup/usb", setup_usb_info, "setup")
    r("POST", "/setup/usb", setup_usb, "setup")
    r("POST", "/setup/target", setup_target, "setup")
    r("POST", "/setup/smtp", setup_smtp, "setup")
    r("POST", "/setup/finish", setup_finish, "setup")

    # Auth and profile ------------------------------------------------------

    def login(req: Request):
        if not ctx.setup.completed():
            raise ApiError(409, "setup_required")
        v = Validator(req.body)
        username = v.string("username", required=True, max_len=64)
        password = req.body.get("password") or ""
        v.raise_if_errors()
        try:
            token, user = ctx.auth.login(username, str(password))
        except AuthError as exc:
            db.audit(None, "login.failed", username, req.headers.get("X-Client-IP", ""))
            raise ApiError(401 if exc.code == "auth_failed" else 423, exc.code) from exc
        db.audit(user, "login", "", req.headers.get("X-Client-IP", ""))
        return {"token": token, "user": public_user(user)}

    def logout(req: Request):
        ctx.auth.logout(req.token)
        return {"ok": True}

    def me(req: Request):
        return {"user": public_user(req.user)}

    def me_update(req: Request):
        v = Validator(req.body)
        email = v.email("email")
        locale = v.choice("locale", LOCALES, req.user["locale"])
        v.raise_if_errors()
        db.run("UPDATE users SET email = ?, locale = ? WHERE id = ?", (email, locale, req.user["id"]))
        return {"user": public_user(ctx.auth.get_user(req.user["id"]))}

    def me_password(req: Request):
        if not verify_password(str(req.body.get("current") or ""), req.user["password_hash"]):
            raise ValidationError({"current": "wrong_password"})
        v = Validator(req.body)
        new = v.password("new")
        v.raise_if_errors()
        if new == req.body.get("current"):
            raise ValidationError({"new": "same_password"})
        ctx.auth.set_password(req.user["id"], new)
        db.audit(req.user, "password.change")
        token, user = ctx.auth.login(req.user["username"], new)
        return {"token": token, "user": public_user(user)}

    r("POST", "/auth/login", login, "public")
    r("POST", "/auth/logout", logout, "viewer")
    r("GET", "/me", me, "viewer")
    r("PUT", "/me", me_update, "viewer")
    r("POST", "/me/password", me_password, "viewer")

    # Users -----------------------------------------------------------------

    def users_list(req: Request):
        return {"users": [public_user(u) for u in db.all("SELECT * FROM users ORDER BY username")]}

    def user_create(req: Request):
        v = Validator(req.body)
        username = v.string("username", required=True, max_len=32, pattern=USERNAME_RE)
        email = v.email("email")
        role = v.choice("role", tuple(ROLES), "viewer")
        locale = v.choice("locale", LOCALES, "en")
        v.raise_if_errors()
        if ctx.auth.find_user(username):
            raise ValidationError({"username": "taken"})
        password = generate_password()
        uid = ctx.auth.create_user(username, email, role, locale, password, must_change_pw=True)
        db.audit(req.user, "user.create", username, role)
        return 201, {"user": public_user(ctx.auth.get_user(uid)), "temporary_password": password}

    def _user_or_404(req: Request) -> dict[str, Any]:
        user = ctx.auth.get_user(req.int_param("id"))
        if user is None:
            raise ApiError(404, "not_found")
        return user

    def _guard_last_admin(user: dict[str, Any], new_role: str | None, disabling: bool) -> None:
        if user["role"] == "admin" and not user["disabled"] and (new_role not in (None, "admin") or disabling):
            if ctx.auth.active_admins() <= 1:
                raise ApiError(409, "last_admin")

    def user_update(req: Request):
        user = _user_or_404(req)
        v = Validator(req.body)
        email = v.email("email")
        role = v.choice("role", tuple(ROLES), user["role"])
        locale = v.choice("locale", LOCALES, user["locale"])
        disabled = v.boolean("disabled", bool(user["disabled"]))
        v.raise_if_errors()
        _guard_last_admin(user, role, disabled and not user["disabled"])
        db.run("UPDATE users SET email = ?, role = ?, locale = ?, disabled = ? WHERE id = ?",
               (email, role, locale, int(disabled), user["id"]))
        if disabled:
            db.run("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
        db.audit(req.user, "user.update", user["username"], f"role={role} disabled={disabled}")
        return {"user": public_user(ctx.auth.get_user(user["id"]))}

    def user_reset_password(req: Request):
        user = _user_or_404(req)
        password = generate_password()
        ctx.auth.set_password(user["id"], password, must_change=True)
        db.audit(req.user, "user.reset_password", user["username"])
        return {"temporary_password": password}

    def user_unlock(req: Request):
        user = _user_or_404(req)
        db.run("UPDATE users SET failed_logins = 0, locked_until = 0 WHERE id = ?", (user["id"],))
        db.audit(req.user, "user.unlock", user["username"])
        return {"ok": True}

    def user_delete(req: Request):
        user = _user_or_404(req)
        if user["id"] == req.user["id"]:
            raise ApiError(409, "cannot_delete_self")
        _guard_last_admin(user, None, True)
        db.run("DELETE FROM users WHERE id = ?", (user["id"],))
        db.audit(req.user, "user.delete", user["username"])
        return {"ok": True}

    r("GET", "/users", users_list, "admin")
    r("POST", "/users", user_create, "admin")
    r("PUT", "/users/{id}", user_update, "admin")
    r("POST", "/users/{id}/reset-password", user_reset_password, "admin")
    r("POST", "/users/{id}/unlock", user_unlock, "admin")
    r("DELETE", "/users/{id}", user_delete, "admin")

    # Status ----------------------------------------------------------------

    def status(req: Request):
        counts = {row["status"]: row["n"] for row in db.all(
            "SELECT status, COUNT(*) AS n FROM uploads GROUP BY status")}
        ok, reason = ctx.gadget.available()
        current = ctx.uploader.current
        return {
            "version": __version__,
            "hostname": ctx.hostname(),
            "addresses": system.ip_addresses() if not ctx.simulated else ["127.0.0.1"],
            "model": system.pi_model(),
            "uptime": system.uptime_seconds(),
            "cpu_temp": system.cpu_temperature(),
            "disk": system.disk_usage(ctx.paths.lib),
            "simulated": ctx.simulated,
            "usb": {
                "enabled": ctx.usb_settings()["enabled"],
                "available": ok,
                "unavailable_reason": reason,
                "state": ctx.gadget.state(),
                "image": ctx.gadget.image_info(),
                "monitor": dict(ctx.monitor.state),
                "last_sync": db.get_setting("last_sync"),
            },
            "uploads": {"pending": counts.get("pending", 0), "failed": counts.get("failed", 0),
                        "done": counts.get("done", 0), "current": current},
            "targets": db.scalar("SELECT COUNT(*) FROM targets WHERE enabled = 1") or 0,
            "mail_configured": ctx.mailer.configured(),
            "mail_queue": db.scalar("SELECT COUNT(*) FROM mail_queue WHERE sent_at IS NULL") or 0,
        }

    r("GET", "/status", status, "viewer")

    # USB gadget --------------------------------------------------------------

    def usb_get(req: Request):
        ok, reason = ctx.gadget.available()
        return {"settings": ctx.usb_settings(), "defaults": DEFAULT_USB, "state": ctx.gadget.state(),
                "image": ctx.gadget.image_info(), "available": ok, "unavailable_reason": reason,
                "max_size_mb": max_image_mb(ctx)}

    def usb_put(req: Request):
        old = ctx.usb_settings()
        cfg = parse_usb(req.body, old, max_image_mb(ctx))
        db.set_setting("usb", cfg)
        identity = ("enabled", "removable", "read_only", "cdrom", "vendor_id", "product_id",
                    "manufacturer", "product", "serial", "max_power_ma")
        error = ""
        if any(old[k] != cfg[k] for k in identity) and ctx.gadget.image_exists():
            error = apply_gadget(ctx)
        changed = [k for k in cfg if cfg[k] != old[k]]
        db.audit(req.user, "usb.update", "", ", ".join(changed))
        image_changes = [k for k in ("size_mb", "filesystem", "label", "partition_table") if k in changed]
        return {"settings": cfg, "gadget_error": error, "image_rebuild_needed": bool(image_changes)}

    def usb_attach(req: Request):
        try:
            if not ctx.gadget.state()["configured"]:
                ctx.gadget.apply(ctx.usb_settings())
            else:
                ctx.gadget.attach()
        except (GadgetError, OSError, CommandError) as exc:
            raise ApiError(500, "gadget_error", str(exc)) from exc
        db.audit(req.user, "usb.attach")
        return {"state": ctx.gadget.state()}

    def usb_detach(req: Request):
        try:
            ctx.gadget.detach()
        except (GadgetError, OSError) as exc:
            raise ApiError(500, "gadget_error", str(exc)) from exc
        db.audit(req.user, "usb.detach")
        return {"state": ctx.gadget.state()}

    def usb_sync(req: Request):
        if not ctx.gadget.image_exists():
            raise ApiError(409, "no_image")
        ctx.monitor.request_sync()
        db.audit(req.user, "usb.sync")
        return {"ok": True}

    def usb_image(req: Request):
        if req.body.get("confirm") is not True:
            raise ValidationError({"confirm": "required"})
        cfg = ctx.usb_settings()
        create_image(ctx, cfg)
        error = apply_gadget(ctx) if cfg["enabled"] else ""
        db.audit(req.user, "usb.image", "", f"{cfg['size_mb']} MB {cfg['filesystem']}")
        return {"ok": True, "gadget_error": error, "image": ctx.gadget.image_info()}

    def files(req: Request):
        rows = db.all("SELECT * FROM file_index ORDER BY mtime DESC LIMIT ?", (_limit(req, 200, 2000),))
        for row in rows:
            row["uploaded"] = bool(row["uploaded"])
        return {"files": rows}

    def file_events(req: Request):
        return {"events": db.all("SELECT id, time, path, event, size FROM file_events ORDER BY id DESC LIMIT ?",
                                 (_limit(req),))}

    r("GET", "/usb", usb_get, "viewer")
    r("PUT", "/usb", usb_put, "manager")
    r("POST", "/usb/attach", usb_attach, "operator")
    r("POST", "/usb/detach", usb_detach, "operator")
    r("POST", "/usb/sync", usb_sync, "operator")
    r("POST", "/usb/image", usb_image, "admin")
    r("GET", "/files", files, "viewer")
    r("GET", "/file-events", file_events, "viewer")

    # Targets ---------------------------------------------------------------

    def targets_list(req: Request):
        return {"targets": [target_public(ctx, t) for t in db.all("SELECT * FROM targets ORDER BY name")],
                "protocols": list(PROTOCOLS)}

    def _target_or_404(req: Request) -> dict[str, Any]:
        row = db.one("SELECT * FROM targets WHERE id = ?", (req.int_param("id"),))
        if row is None:
            raise ApiError(404, "not_found")
        return row

    def target_get(req: Request):
        return {"target": target_public(ctx, _target_or_404(req))}

    def target_create(req: Request):
        fields, password = parse_target(req.body)
        now = time.time()
        tid = db.run(
            "INSERT INTO targets(name, protocol, host, port, path, username, secret, options, enabled, "
            "created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (fields["name"], fields["protocol"], fields["host"], fields["port"], fields["path"],
             fields["username"], ctx.secrets.encrypt(password or ""), fields["options"], fields["enabled"],
             now, now))
        db.audit(req.user, "target.create", fields["name"], fields["protocol"])
        return 201, {"target": target_public(ctx, db.one("SELECT * FROM targets WHERE id = ?", (tid,)))}

    def target_update(req: Request):
        row = _target_or_404(req)
        fields, password = parse_target(req.body)
        secret = row["secret"] if password is None else ctx.secrets.encrypt(password)
        db.run("UPDATE targets SET name = ?, protocol = ?, host = ?, port = ?, path = ?, username = ?, "
               "secret = ?, options = ?, enabled = ?, updated_at = ? WHERE id = ?",
               (fields["name"], fields["protocol"], fields["host"], fields["port"], fields["path"],
                fields["username"], secret, fields["options"], fields["enabled"], time.time(), row["id"]))
        db.audit(req.user, "target.update", fields["name"])
        ctx.uploader.wake()
        return {"target": target_public(ctx, db.one("SELECT * FROM targets WHERE id = ?", (row["id"],)))}

    def target_delete(req: Request):
        row = _target_or_404(req)
        db.run("DELETE FROM targets WHERE id = ?", (row["id"],))
        ctx.uploader.cleanup_orphans()
        db.audit(req.user, "target.delete", row["name"])
        return {"ok": True}

    def target_test_saved(req: Request):
        row = _target_or_404(req)
        fields = {k: row[k] for k in ("name", "protocol", "host", "port", "path", "username", "options")}
        result = run_target_test(ctx, fields, ctx.secrets.decrypt(row["secret"]))
        db.log("info" if result["ok"] else "warning", "target",
               f"Connection test for {row['name']}: {'ok' if result['ok'] else result['error']}")
        return result

    def target_test_unsaved(req: Request):
        fields, password = parse_target(req.body)
        if password is None and req.body.get("id"):
            row = db.one("SELECT secret FROM targets WHERE id = ?", (int(req.body["id"]),))
            password = ctx.secrets.decrypt(row["secret"]) if row else ""
        return run_target_test(ctx, fields, password or "")

    r("GET", "/targets", targets_list, "viewer")
    r("POST", "/targets", target_create, "manager")
    r("POST", "/targets/test", target_test_unsaved, "manager")
    r("GET", "/targets/{id}", target_get, "viewer")
    r("PUT", "/targets/{id}", target_update, "manager")
    r("DELETE", "/targets/{id}", target_delete, "manager")
    r("POST", "/targets/{id}/test", target_test_saved, "manager")

    # Uploads ---------------------------------------------------------------

    def uploads_list(req: Request):
        status_filter = req.q("status")
        sql = ("SELECT u.id, u.status, u.attempts, u.last_error, u.remote_path, u.created_at, u.finished_at, "
               "u.next_try, e.path, e.size, t.name AS target FROM uploads u "
               "JOIN file_events e ON e.id = u.event_id JOIN targets t ON t.id = u.target_id")
        params: list[Any] = []
        if status_filter in ("pending", "failed", "done", "discarded"):
            sql += " WHERE u.status = ?"
            params.append(status_filter)
        sql += " ORDER BY u.id DESC LIMIT ?"
        params.append(_limit(req))
        return {"uploads": db.all(sql, params), "current": ctx.uploader.current}

    def upload_retry(req: Request):
        n = ctx.uploader.retry(req.int_param("id"))
        if not n:
            raise ApiError(409, "not_retryable")
        db.audit(req.user, "upload.retry", req.params["id"])
        return {"retried": n}

    def uploads_retry_failed(req: Request):
        n = ctx.uploader.retry(None)
        db.audit(req.user, "upload.retry_all", "", str(n))
        return {"retried": n}

    def upload_discard(req: Request):
        if not ctx.uploader.discard(req.int_param("id")):
            raise ApiError(409, "not_discardable")
        db.audit(req.user, "upload.discard", req.params["id"])
        return {"ok": True}

    r("GET", "/uploads", uploads_list, "viewer")
    r("POST", "/uploads/retry-failed", uploads_retry_failed, "operator")
    r("POST", "/uploads/{id}/retry", upload_retry, "operator")
    r("POST", "/uploads/{id}/discard", upload_discard, "manager")

    # Notifications -----------------------------------------------------------

    def smtp_get(req: Request):
        return {"smtp": smtp_public(ctx.mailer.settings())}

    def smtp_put(req: Request):
        cfg = parse_smtp(ctx, req.body, ctx.mailer.settings())
        db.set_setting("smtp", cfg)
        db.audit(req.user, "smtp.update", cfg["host"])
        ctx.mailer.wake()
        return {"smtp": smtp_public(cfg)}

    def smtp_test(req: Request):
        v = Validator(req.body)
        to = v.email("to", required=True)
        v.raise_if_errors()
        try:
            ctx.mailer.send_test(to, req.user["locale"])
        except MailError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True}

    def rules_list(req: Request):
        return {"rules": [rule_public(x) for x in db.all("SELECT * FROM notify_rules ORDER BY name")],
                "event_types": list(EVENT_TYPES)}

    def rule_create(req: Request):
        f = parse_rule(req.body)
        rid = db.run("INSERT INTO notify_rules(name, events, pattern, recipients, mode, digest_minutes, enabled) "
                     "VALUES(?, ?, ?, ?, ?, ?, ?)",
                     (f["name"], f["events"], f["pattern"], f["recipients"], f["mode"], f["digest_minutes"],
                      f["enabled"]))
        db.audit(req.user, "rule.create", f["name"])
        return 201, {"rule": rule_public(db.one("SELECT * FROM notify_rules WHERE id = ?", (rid,)))}

    def rule_update(req: Request):
        rid = req.int_param("id")
        if not db.one("SELECT id FROM notify_rules WHERE id = ?", (rid,)):
            raise ApiError(404, "not_found")
        f = parse_rule(req.body)
        db.run("UPDATE notify_rules SET name = ?, events = ?, pattern = ?, recipients = ?, mode = ?, "
               "digest_minutes = ?, enabled = ? WHERE id = ?",
               (f["name"], f["events"], f["pattern"], f["recipients"], f["mode"], f["digest_minutes"],
                f["enabled"], rid))
        db.audit(req.user, "rule.update", f["name"])
        return {"rule": rule_public(db.one("SELECT * FROM notify_rules WHERE id = ?", (rid,)))}

    def rule_delete(req: Request):
        rid = req.int_param("id")
        db.run("DELETE FROM notify_rules WHERE id = ?", (rid,))
        db.audit(req.user, "rule.delete", str(rid))
        return {"ok": True}

    def mail_queue(req: Request):
        return {"mails": db.all("SELECT id, created_at, recipients, subject, attempts, last_error, sent_at "
                                "FROM mail_queue ORDER BY id DESC LIMIT ?", (_limit(req, 50),))}

    r("GET", "/smtp", smtp_get, "manager")
    r("PUT", "/smtp", smtp_put, "manager")
    r("POST", "/smtp/test", smtp_test, "manager")
    r("GET", "/rules", rules_list, "manager")
    r("POST", "/rules", rule_create, "manager")
    r("PUT", "/rules/{id}", rule_update, "manager")
    r("DELETE", "/rules/{id}", rule_delete, "manager")
    r("GET", "/mail-queue", mail_queue, "manager")

    # Logs ------------------------------------------------------------------

    def events(req: Request):
        sql, params = "SELECT * FROM events", []
        level = req.q("level")
        if level in ("info", "warning", "error"):
            sql += " WHERE level = ?"
            params.append(level)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(_limit(req, 200))
        return {"events": db.all(sql, params)}

    def audit(req: Request):
        return {"audit": db.all("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (_limit(req, 200),))}

    r("GET", "/events", events, "viewer")
    r("GET", "/audit", audit, "admin")

    # System ----------------------------------------------------------------

    def system_get(req: Request):
        return {"hostname": system.hostname(), "timezone": system.timezone(),
                "timezones": system.list_timezones(), "model": system.pi_model(), "simulated": ctx.simulated}

    def system_put(req: Request):
        result = apply_system_settings(req.body)
        db.audit(req.user, "system.update", "", json.dumps(result))
        return result

    def system_power(action: str):
        def handler(req: Request):
            db.audit(req.user, f"system.{action}")
            if ctx.simulated:
                return {"ok": True, "simulated": True}
            ctx.defer(system.reboot if action == "reboot" else system.poweroff)
            return {"ok": True}
        return handler

    def system_setup_reset(req: Request):
        wipe = bool(req.body.get("wipe_users"))
        db.audit(req.user, "system.setup_reset", "", f"wipe_users={wipe}")
        ctx.setup.reset(wipe_users=wipe)
        return {"ok": True}

    def ssh_key_get(req: Request):
        pub = ctx.paths.ssh_key.with_suffix(".pub")
        return {"public_key": pub.read_text().strip() if pub.exists() else ""}

    def ssh_key_generate(req: Request):
        key = ctx.paths.ssh_key
        if key.exists() and not req.body.get("regenerate"):
            raise ApiError(409, "key_exists")
        key.unlink(missing_ok=True)
        key.with_suffix(".pub").unlink(missing_ok=True)
        try:
            system.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", f"netusbflash@{ctx.hostname()}",
                        "-f", str(key)], timeout=30)
        except CommandError as exc:
            raise ApiError(500, "keygen_failed", str(exc)) from exc
        db.audit(req.user, "ssh_key.generate")
        return {"public_key": key.with_suffix(".pub").read_text().strip()}

    r("GET", "/system", system_get, "admin")
    r("PUT", "/system", system_put, "admin")
    r("POST", "/system/reboot", system_power("reboot"), "admin")
    r("POST", "/system/poweroff", system_power("poweroff"), "admin")
    r("POST", "/system/setup-reset", system_setup_reset, "admin")
    r("GET", "/system/ssh-key", ssh_key_get, "manager")
    r("POST", "/system/ssh-key", ssh_key_generate, "manager")

"""Email notifications: rules, digests, SMTP client and a persistent queue."""

from __future__ import annotations

import fnmatch
import logging
import smtplib
import ssl
import threading
import time
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .service import Context

log = logging.getLogger(__name__)

EVENT_TYPES = ("created", "modified", "deleted", "uploaded", "upload_failed")
SECURITY_MODES = ("starttls", "ssl", "none")

DEFAULT_SMTP: dict[str, Any] = {
    "host": "",
    "port": 587,
    "security": "starttls",
    "username": "",
    "password": "",          # stored encrypted
    "sender": "",
    "sender_name": "NetUSBFlash",
    "verify_tls": True,
}

TEXT = {
    "en": {
        "subject": "[{host}] {count} file event(s)",
        "intro": "NetUSBFlash on {host} reports:",
        "created": "New files",
        "modified": "Changed files",
        "deleted": "Deleted files",
        "uploaded": "Uploaded files",
        "upload_failed": "Failed uploads",
        "footer": "This message was sent automatically by NetUSBFlash (rule: {rule}).",
        "test_subject": "[{host}] NetUSBFlash test email",
        "test_body": "This is a test email from NetUSBFlash on {host}. Your SMTP settings work.",
    },
    "de": {
        "subject": "[{host}] {count} Datei-Ereignis(se)",
        "intro": "NetUSBFlash auf {host} meldet:",
        "created": "Neue Dateien",
        "modified": "Geänderte Dateien",
        "deleted": "Gelöschte Dateien",
        "uploaded": "Hochgeladene Dateien",
        "upload_failed": "Fehlgeschlagene Uploads",
        "footer": "Diese Nachricht wurde automatisch von NetUSBFlash versendet (Regel: {rule}).",
        "test_subject": "[{host}] NetUSBFlash Testmail",
        "test_body": "Dies ist eine Testmail von NetUSBFlash auf {host}. Die SMTP-Einstellungen funktionieren.",
    },
}

MAX_LINES_PER_SECTION = 200


class MailError(Exception):
    pass


class Notifier:
    """Turns file events into pending notification items per matching rule."""

    def __init__(self, ctx: "Context"):
        self.ctx = ctx

    def record(self, event: str, path: str, detail: str = "") -> None:
        name = path.rsplit("/", 1)[-1].lower()
        rules = self.ctx.db.all("SELECT * FROM notify_rules WHERE enabled = 1")
        now = time.time()
        for rule in rules:
            if event not in rule["events"].split(","):
                continue
            pats = [p.strip().lower() for p in (rule["pattern"] or "*").split(",") if p.strip()] or ["*"]
            if not any(fnmatch.fnmatch(name, p) for p in pats):
                continue
            self.ctx.db.run(
                "INSERT INTO notify_items(rule_id, time, event, path, detail) VALUES(?, ?, ?, ?, ?)",
                (rule["id"], now, event, path, detail),
            )
        if rules:
            self.ctx.mailer.wake()


class Mailer(threading.Thread):
    def __init__(self, ctx: "Context"):
        super().__init__(name="mailer", daemon=True)
        self.ctx = ctx
        self.stop_event = threading.Event()
        self._wake = threading.Event()

    def wake(self) -> None:
        self._wake.set()

    def stop(self) -> None:
        self.stop_event.set()
        self._wake.set()

    def settings(self) -> dict[str, Any]:
        return self.ctx.db.get_dict_setting("smtp", DEFAULT_SMTP)

    def configured(self) -> bool:
        cfg = self.settings()
        return bool(cfg["host"] and cfg["sender"])

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.collect()
                self.send_queue()
            except Exception as exc:
                log.exception("mailer loop failed")
                self.ctx.db.log("error", "mail", f"Mailer error: {exc}")
            self._wake.wait(10)
            self._wake.clear()

    # Composing.

    def collect(self) -> None:
        db = self.ctx.db
        now = time.time()
        for rule in db.all("SELECT * FROM notify_rules"):
            items = db.all("SELECT * FROM notify_items WHERE rule_id = ? AND sent = 0 ORDER BY id", (rule["id"],))
            if not items:
                continue
            if rule["mode"] == "digest" and now - items[0]["time"] < rule["digest_minutes"] * 60:
                continue
            recipients = [r for r in rule["recipients"].split(",") if r]
            for locale, group in self._group_by_locale(recipients).items():
                subject, body = self.compose(rule, items, locale)
                self.enqueue(group, subject, body)
            with db.transaction() as conn:
                conn.executemany("UPDATE notify_items SET sent = 1 WHERE id = ?", [(i["id"],) for i in items])

    def _group_by_locale(self, recipients: list[str]) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {}
        for address in recipients:
            user = self.ctx.db.one("SELECT locale FROM users WHERE lower(email) = lower(?) LIMIT 1", (address,))
            locale = user["locale"] if user and user["locale"] in TEXT else "en"
            groups.setdefault(locale, []).append(address)
        return groups

    def compose(self, rule: dict, items: list[dict], locale: str) -> tuple[str, str]:
        text = TEXT.get(locale, TEXT["en"])
        host = self.ctx.hostname()
        lines = [text["intro"].format(host=host), ""]
        for event in EVENT_TYPES:
            section = [i for i in items if i["event"] == event]
            if not section:
                continue
            lines.append(f"{text[event]} ({len(section)}):")
            for item in section[:MAX_LINES_PER_SECTION]:
                stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(item["time"]))
                detail = f"  [{item['detail']}]" if item["detail"] else ""
                lines.append(f"  {stamp}  {item['path']}{detail}")
            if len(section) > MAX_LINES_PER_SECTION:
                lines.append(f"  … +{len(section) - MAX_LINES_PER_SECTION}")
            lines.append("")
        lines += ["--", text["footer"].format(rule=rule["name"])]
        subject = text["subject"].format(host=host, count=len(items))
        return subject, "\n".join(lines)

    # Queue.

    def enqueue(self, recipients: list[str], subject: str, body: str) -> None:
        self.ctx.db.run(
            "INSERT INTO mail_queue(created_at, recipients, subject, body) VALUES(?, ?, ?, ?)",
            (time.time(), ",".join(recipients), subject, body),
        )

    def send_queue(self) -> None:
        if not self.configured():
            return
        db = self.ctx.db
        now = time.time()
        for row in db.all("SELECT * FROM mail_queue WHERE sent_at IS NULL AND attempts < 8 AND next_try <= ? "
                          "ORDER BY id LIMIT 10", (now,)):
            try:
                self.send(row["recipients"].split(","), row["subject"], row["body"])
            except MailError as exc:
                attempts = row["attempts"] + 1
                db.run("UPDATE mail_queue SET attempts = ?, last_error = ?, next_try = ? WHERE id = ?",
                       (attempts, str(exc), now + min(60 * 2 ** attempts, 3600), row["id"]))
                db.log("warning", "mail", f"Sending email failed (try {attempts}): {exc}")
            else:
                db.run("UPDATE mail_queue SET sent_at = ?, last_error = '' WHERE id = ?", (time.time(), row["id"]))

    # SMTP.

    def send(self, recipients: list[str], subject: str, body: str, cfg: dict[str, Any] | None = None) -> None:
        cfg = cfg or self.settings()
        if not cfg["host"] or not cfg["sender"]:
            raise MailError("SMTP is not configured")
        msg = EmailMessage()
        msg["From"] = formataddr((cfg["sender_name"] or "NetUSBFlash", cfg["sender"]))
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg["Message-ID"] = make_msgid(domain=cfg["sender"].split("@")[-1])
        msg.set_content(body)
        context = ssl.create_default_context()
        if not cfg.get("verify_tls", True):
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        password = self.ctx.secrets.decrypt(cfg.get("password", ""))
        try:
            if cfg["security"] == "ssl":
                server: smtplib.SMTP = smtplib.SMTP_SSL(cfg["host"], int(cfg["port"]), context=context, timeout=30)
            else:
                server = smtplib.SMTP(cfg["host"], int(cfg["port"]), timeout=30)
            with server:
                server.ehlo()
                if cfg["security"] == "starttls":
                    server.starttls(context=context)
                    server.ehlo()
                if cfg["username"]:
                    server.login(cfg["username"], password)
                server.send_message(msg)
        except (smtplib.SMTPException, OSError, ssl.SSLError) as exc:
            raise MailError(str(exc) or exc.__class__.__name__) from exc

    def send_test(self, recipient: str, locale: str, cfg: dict[str, Any] | None = None) -> None:
        text = TEXT.get(locale, TEXT["en"])
        host = self.ctx.hostname()
        self.send([recipient], text["test_subject"].format(host=host), text["test_body"].format(host=host), cfg)

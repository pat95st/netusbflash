"""Email notifications: rules, digests, SMTP client and a persistent queue."""

from __future__ import annotations

import fnmatch
import re
import logging
import smtplib
import ssl
import threading
import time
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from html import escape

from . import __version__
from .htmlsafe import sanitise, to_text
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
        "subject": "[{{host}}] {{count}} file event(s)",
        "intro": "NetUSBFlash on {{host}} reports:",
        "created": "New files",
        "modified": "Changed files",
        "deleted": "Deleted files",
        "uploaded": "Uploaded files",
        "upload_failed": "Failed uploads",
        "footer": "This message was sent automatically by NetUSBFlash (rule: {{rule}}).",
        "test_subject": "[{host}] NetUSBFlash test email",
        "test_body": "This is a test email from NetUSBFlash on {host}. Your SMTP settings work.",
    },
    "de": {
        "subject": "[{{host}}] {{count}} Datei-Ereignis(se)",
        "intro": "NetUSBFlash auf {{host}} meldet:",
        "created": "Neue Dateien",
        "modified": "Geänderte Dateien",
        "deleted": "Gelöschte Dateien",
        "uploaded": "Hochgeladene Dateien",
        "upload_failed": "Fehlgeschlagene Uploads",
        "footer": "Diese Nachricht wurde automatisch von NetUSBFlash versendet (Regel: {{rule}}).",
        "test_subject": "[{host}] NetUSBFlash Testmail",
        "test_body": "Dies ist eine Testmail von NetUSBFlash auf {host}. Die SMTP-Einstellungen funktionieren.",
    },
}

MAX_LINES_PER_SECTION = 200

# Placeholders usable in subject and body templates, written as {{name}}.
PLACEHOLDERS = (
    "host", "rule", "count", "date", "time", "version", "files", "file_names",
    "created_count", "modified_count", "deleted_count", "uploaded_count", "failed_count",
    "created_list", "modified_list", "deleted_list", "uploaded_list", "failed_list",
)
_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")
# Placeholders that expand to a list: a paragraph that holds nothing else is
# replaced as a whole (editors put every line into a <p>, and <ul> may not be
# nested in <p>).
_BLOCK_PARAGRAPH_RE = re.compile(r"<p>\s*(\{\{\s*(?:files|[a-z]+_list)\s*\}\})\s*</p>")
_EVENT_KEY = {"created": "created", "modified": "modified", "deleted": "deleted",
              "uploaded": "uploaded", "upload_failed": "failed"}


def default_templates(locale: str) -> dict[str, str]:
    text = TEXT.get(locale, TEXT["en"])
    body = (
        f"<p>{escape(text['intro'])}</p>"
        "{{files}}"
        "<hr>"
        f"<p><span style=\"color: #6c757d\">{escape(text['footer'])}</span></p>"
    )
    return {"subject": text["subject"], "body": body}


def render(template: str, values: dict[str, tuple[str, str]], html_mode: bool) -> str:
    """Replace {{name}} with the text or HTML value; unknown names stay as they are."""
    def repl(match: re.Match[str]) -> str:
        pair = values.get(match.group(1))
        if pair is None:
            return match.group(0)
        return pair[1] if html_mode else pair[0]
    return _PLACEHOLDER_RE.sub(repl, template)


def wrap_html(fragment: str) -> str:
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"></head>"
        "<body style=\"margin:0;padding:16px;font-family:Arial,Helvetica,sans-serif;font-size:14px;"
        "line-height:1.5;color:#212529\">" + fragment + "</body></html>"
    )


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
                subject, html_body, text = self.compose(rule, items, locale)
                self.enqueue(group, subject, text, html_body)
            with db.transaction() as conn:
                conn.executemany("UPDATE notify_items SET sent = 1 WHERE id = ?", [(i["id"],) for i in items])

    def _group_by_locale(self, recipients: list[str]) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {}
        for address in recipients:
            user = self.ctx.db.one("SELECT locale FROM users WHERE lower(email) = lower(?) LIMIT 1", (address,))
            locale = user["locale"] if user and user["locale"] in TEXT else "en"
            groups.setdefault(locale, []).append(address)
        return groups

    def placeholder_values(self, rule: dict, items: list[dict], locale: str) -> dict[str, tuple[str, str]]:
        """Values for every placeholder as (plain text, HTML)."""
        text = TEXT.get(locale, TEXT["en"])
        now = time.time()
        values: dict[str, tuple[str, str]] = {}

        def plain(name: str, value: Any) -> None:
            values[name] = (str(value), escape(str(value)))

        plain("host", self.ctx.hostname())
        plain("rule", rule.get("name", ""))
        plain("count", len(items))
        plain("date", time.strftime("%d.%m.%Y" if locale == "de" else "%Y-%m-%d", time.localtime(now)))
        plain("time", time.strftime("%H:%M", time.localtime(now)))
        plain("version", __version__)
        names = [i["path"].rsplit("/", 1)[-1] for i in items]
        short = ", ".join(names[:5]) + (f" (+{len(names) - 5})" if len(names) > 5 else "")
        plain("file_names", short)

        sections_text, sections_html = [], []
        for event in EVENT_TYPES:
            key = _EVENT_KEY[event]
            section = [i for i in items if i["event"] == event]
            plain(f"{key}_count", len(section))
            lines_text, lines_html = [], []
            for item in section[:MAX_LINES_PER_SECTION]:
                stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(item["time"]))
                detail = f" [{item['detail']}]" if item["detail"] else ""
                lines_text.append(f"  {stamp}  {item['path']}{detail}")
                lines_html.append(
                    f"<li><span style=\"color: #6c757d\">{escape(stamp)}</span> "
                    f"{escape(item['path'])}{escape(detail)}</li>")
            if len(section) > MAX_LINES_PER_SECTION:
                more = f"… +{len(section) - MAX_LINES_PER_SECTION}"
                lines_text.append(f"  {more}")
                lines_html.append(f"<li>{escape(more)}</li>")
            list_html = f"<ul>{''.join(lines_html)}</ul>" if lines_html else ""
            values[f"{key}_list"] = ("\n".join(lines_text), list_html)
            if section:
                heading = f"{text[event]} ({len(section)})"
                sections_text.append(f"{heading}:\n" + "\n".join(lines_text))
                sections_html.append(f"<p><strong>{escape(heading)}</strong></p>{list_html}")
        values["files"] = ("\n\n".join(sections_text), "".join(sections_html))
        return values

    def compose(self, rule: dict, items: list[dict], locale: str) -> tuple[str, str, str]:
        """Return (subject, html fragment, plain text) for a rule's pending items."""
        defaults = default_templates(locale)
        values = self.placeholder_values(rule, items, locale)
        subject_tpl = (rule.get("subject_template") or "").strip() or defaults["subject"]
        body_tpl = (rule.get("body_template") or "").strip() or defaults["body"]
        subject = " ".join(render(subject_tpl, values, html_mode=False).split())[:250]
        html_body = render(_BLOCK_PARAGRAPH_RE.sub(r"\1", sanitise(body_tpl)), values, html_mode=True)
        return subject, html_body, to_text(html_body)

    def preview(self, rule: dict, locale: str) -> dict[str, str]:
        now = time.time()
        sample = [
            {"event": "created", "path": "REC/SONG01.WAV", "time": now - 300, "detail": ""},
            {"event": "created", "path": "REC/SONG02.WAV", "time": now - 120, "detail": ""},
            {"event": "uploaded", "path": "REC/SONG01.WAV", "time": now - 60, "detail": "NAS"},
        ]
        subject, html_body, text = self.compose(rule, sample, locale)
        return {"subject": subject, "html": html_body, "text": text}

    # Queue.

    def enqueue(self, recipients: list[str], subject: str, body: str, html_body: str = "") -> None:
        self.ctx.db.run(
            "INSERT INTO mail_queue(created_at, recipients, subject, body, html) VALUES(?, ?, ?, ?, ?)",
            (time.time(), ",".join(recipients), subject, body, html_body),
        )

    def send_queue(self) -> None:
        if not self.configured():
            return
        db = self.ctx.db
        now = time.time()
        for row in db.all("SELECT * FROM mail_queue WHERE sent_at IS NULL AND attempts < 8 AND next_try <= ? "
                          "ORDER BY id LIMIT 10", (now,)):
            try:
                self.send(row["recipients"].split(","), row["subject"], row["body"], html_body=row.get("html") or None)
            except MailError as exc:
                attempts = row["attempts"] + 1
                db.run("UPDATE mail_queue SET attempts = ?, last_error = ?, next_try = ? WHERE id = ?",
                       (attempts, str(exc), now + min(60 * 2 ** attempts, 3600), row["id"]))
                db.log("warning", "mail", f"Sending email failed (try {attempts}): {exc}")
            else:
                db.run("UPDATE mail_queue SET sent_at = ?, last_error = '' WHERE id = ?", (time.time(), row["id"]))

    # SMTP.

    def send(self, recipients: list[str], subject: str, body: str, cfg: dict[str, Any] | None = None,
             html_body: str | None = None) -> None:
        cfg = cfg or self.settings()
        if not cfg["host"] or not cfg["sender"]:
            raise MailError("SMTP is not configured")
        msg = EmailMessage()
        msg["From"] = formataddr((cfg["sender_name"] or "NetUSBFlash", cfg["sender"]))
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg["Message-ID"] = make_msgid(domain=cfg["sender"].split("@")[-1])
        msg.set_content(body)
        if html_body:
            msg.add_alternative(wrap_html(html_body), subtype="html")
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

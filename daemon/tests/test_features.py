"""Tests for mail templates, file browser, updates and backup."""

import io
import json
import tarfile
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from helpers import Client, ServiceFixture, wait_for

from netusbflash.backup import BackupError, decrypt_secrets, encrypt_secrets, next_due
from netusbflash.htmlsafe import sanitise, to_text
from netusbflash.updater import UpdateError, is_newer, parse_version, pick_release, safe_extract


class HtmlSafeTests(unittest.TestCase):
    def test_strips_dangerous_markup(self):
        out = sanitise('<p onclick="x()">a<script>alert(1)</script></p><a href="javascript:x">l</a>'
                       '<img src=x onerror=1><iframe src="https://x"></iframe><style>p{}</style>')
        self.assertEqual(out, '<p>a</p><a rel="noopener">l</a>')

    def test_keeps_formatting_and_converts_classes(self):
        out = sanitise('<h2 class="ql-align-center">T</h2><p class="ql-indent-2">i</p>'
                       '<span style="color: rgb(230, 0, 0); position: fixed">c</span><a href="https://e.org">e</a>')
        self.assertIn('<h2 style="text-align: center">T</h2>', out)
        self.assertIn('padding-left: 6em', out)
        self.assertIn('style="color: rgb(230, 0, 0)"', out)
        self.assertIn('href="https://e.org"', out)

    def test_placeholder_links_survive(self):
        self.assertIn('href="{{url}}"', sanitise('<a href="{{url}}">x</a>'))

    def test_text_version(self):
        self.assertEqual(to_text('<p>Hello <b>you</b></p><ul><li>a</li></ul>'), 'Hello you\n• a')


class TemplateTests(unittest.TestCase):
    def test_list_placeholder_paragraph_is_unwrapped(self):
        from netusbflash.mailer import _BLOCK_PARAGRAPH_RE
        html = "<p>Hi</p><p>{{files}}</p><p> {{ created_list }} </p><p>{{count}}</p>"
        self.assertEqual(_BLOCK_PARAGRAPH_RE.sub(r"\1", html),
                         "<p>Hi</p>{{files}}{{ created_list }}<p>{{count}}</p>")


class VersionTests(unittest.TestCase):
    def test_ordering(self):
        self.assertTrue(is_newer("0.1.0", "0.1.0-alpha.1"))
        self.assertTrue(is_newer("0.1.0-alpha.2", "0.1.0-alpha.1"))
        self.assertTrue(is_newer("0.1.0-beta.1", "0.1.0-alpha.9"))
        self.assertTrue(is_newer("v0.2.0", "0.1.9"))
        self.assertFalse(is_newer("0.1.0-alpha.1", "0.1.0-alpha.1"))
        self.assertFalse(is_newer("garbage", "0.1.0"))
        self.assertIsNone(parse_version("1.2"))

    def test_pick_release(self):
        releases = [
            {"tag_name": "v0.2.0-beta.1", "prerelease": True},
            {"tag_name": "v0.1.1", "prerelease": False},
            {"tag_name": "v0.3.0", "draft": True},
        ]
        self.assertEqual(pick_release(releases, True)["tag_name"], "v0.2.0-beta.1")
        self.assertEqual(pick_release(releases, False)["tag_name"], "v0.1.1")

    def _tar(self, members):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for name, data in members:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        return buf.getvalue()

    def test_safe_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "a.tar.gz"
            archive.write_bytes(self._tar([("netusbflash-0.2.0/VERSION", b"0.2.0\n"),
                                           ("netusbflash-0.2.0/packaging/install.sh", b"#!/bin/sh\n")]))
            root = safe_extract(archive, Path(tmp) / "out")
            self.assertEqual(root.name, "netusbflash-0.2.0")
            evil = Path(tmp) / "evil.tar.gz"
            evil.write_bytes(self._tar([("../escape.txt", b"x")]))
            with self.assertRaises(UpdateError):
                safe_extract(evil, Path(tmp) / "out2")


class BackupUnitTests(unittest.TestCase):
    def test_secret_roundtrip(self):
        blob = encrypt_secrets({"targets": {"1": "pw"}}, "long passphrase")
        self.assertEqual(decrypt_secrets(blob, "long passphrase"), {"targets": {"1": "pw"}})
        with self.assertRaises(BackupError):
            decrypt_secrets(blob, "wrong passphrase")

    def test_next_due(self):
        now = time.mktime((2026, 11, 9, 10, 0, 0, 0, 0, -1))
        tomorrow_3 = time.mktime((2026, 11, 10, 3, 0, 0, 0, 0, -1))
        self.assertEqual(next_due(None, "daily", 3, now), tomorrow_3)
        last = time.mktime((2026, 11, 9, 3, 0, 5, 0, 0, -1))
        self.assertEqual(next_due(last, "daily", 3, now), tomorrow_3)
        self.assertEqual(time.localtime(next_due(last, "weekly", 3, now)).tm_mday, 16)
        self.assertEqual(time.localtime(next_due(last, "monthly", 3, now)).tm_mday, 1)


class FeatureApiTests(unittest.TestCase):
    def setUp(self):
        self.svc = ServiceFixture()
        self.svc.complete_setup()
        self.c = self.svc.client

    def tearDown(self):
        self.svc.close()

    def test_rule_templates_and_preview(self):
        status, body = self.c.call("POST", "/rules", {
            "name": "Custom", "events": ["created"], "recipients": "a@example.com",
            "subject_template": "{{count}} new on {{host}}",
            "body_template": "<p>Hi</p>{{created_list}}<script>x</script>"})
        self.assertEqual(status, 201, body)
        self.assertEqual(body["rule"]["body_template"], "<p>Hi</p>{{created_list}}")
        status, body = self.c.call("POST", "/rules/preview", {
            "name": "Custom", "subject_template": "{{count}} new on {{host}}",
            "body_template": "<p>{{file_names}}</p>{{created_list}}"})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["subject"], "3 new on nuf-test")
        self.assertIn("SONG01.WAV", body["html"])
        self.assertIn("<ul><li>", body["html"])
        status, body = self.c.call("GET", "/rules")
        self.assertIn("files", body["placeholders"])
        self.assertIn("{{files}}", body["defaults"]["body"])

    def test_empty_editor_means_default_template(self):
        status, body = self.c.call("POST", "/rules", {"name": "D", "events": ["created"],
                                                      "recipients": "a@example.com", "body_template": "<p><br></p>"})
        self.assertEqual(body["rule"]["body_template"], "")

    def test_html_mail_sent_with_template(self):
        sent = []
        with mock.patch("netusbflash.mailer.Mailer.send",
                        side_effect=lambda r, s, b, cfg=None, html_body=None: sent.append((s, b, html_body))):
            self.c.call("PUT", "/smtp", {"host": "smtp.example.com", "sender": "pi@example.com"})
            self.c.call("POST", "/rules", {"name": "R", "events": ["created"], "recipients": "a@example.com",
                                           "subject_template": "Neu: {{file_names}}",
                                           "body_template": "<p><strong>{{count}}</strong> neu</p>"})
            self.svc.ctx.notifier.record("created", "REC/A.WAV")
            self.svc.ctx.mailer.collect()
            self.svc.ctx.mailer.send_queue()
        self.assertEqual(sent[0][0], "Neu: A.WAV")
        self.assertIn("<strong>1</strong> neu", sent[0][2])
        self.assertIn("1 neu", sent[0][1])

    def test_browser_modes_and_roles(self):
        status, body = self.c.call("GET", "/browser")
        self.assertEqual(body["mode"], "off")
        status, body = self.c.call("POST", "/browser", {"mode": "edit"})
        self.assertEqual((status, body["mode"]), (200, "edit"))
        self.assertTrue(body["edit_until"] > time.time())
        status, body = self.c.call("POST", "/browser", {"mode": "view"})
        self.assertEqual(body["mode"], "view")
        # A viewer may open the read-only view but not edit mode.
        status, body = self.c.call("POST", "/users", {"username": "vic", "role": "viewer"})
        vic = Client(self.c.socket_path)
        token = vic.call("POST", "/auth/login", {"username": "vic", "password": body["temporary_password"]})[1]["token"]
        vic.token = token
        vic.call("POST", "/me/password", {"current": body["temporary_password"], "new": "vic-password-123"})
        vic.token = vic.call("POST", "/auth/login", {"username": "vic", "password": "vic-password-123"})[1]["token"]
        self.assertEqual(vic.call("POST", "/browser", {"mode": "edit"})[0], 403)
        self.assertEqual(vic.call("POST", "/browser", {"mode": "view"})[0], 200)

    def test_edit_mode_detaches_and_reattaches(self):
        gadget = self.svc.ctx.gadget
        self.assertTrue(gadget.state()["attached"])
        self.c.call("POST", "/browser", {"mode": "edit"})
        self.assertFalse(gadget.state()["attached"])
        self.c.call("POST", "/browser", {"mode": "off"})
        self.assertTrue(gadget.state()["attached"])

    def test_update_check_and_settings(self):
        releases = [{"tag_name": "v9.0.0", "name": "Big", "body": "Notes", "html_url": "https://x",
                     "published_at": "2026-11-01T00:00:00Z", "prerelease": False, "tarball_url": "https://x/t",
                     "assets": [{"name": "netusbflash-9.0.0.tar.gz", "browser_download_url": "https://x/a"},
                                {"name": "netusbflash-9.0.0.tar.gz.sha256", "browser_download_url": "https://x/s"}]}]

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        with mock.patch("urllib.request.urlopen", return_value=Resp(json.dumps(releases).encode())):
            status, body = self.c.call("POST", "/update/check")
        self.assertEqual(status, 200, body)
        self.assertTrue(body["update_available"])
        self.assertEqual(body["latest"]["archive"], "https://x/a")
        self.assertEqual(self.c.call("PUT", "/update", {"repository": "bad repo", "prereleases": True})[0], 422)
        status, body = self.c.call("POST", "/update/os")
        self.assertEqual(body["job"]["kind"], "os")
        self.assertEqual(self.c.call("POST", "/update/os")[1]["error"], "update_failed")  # one job at a time

    def test_backup_export_restore(self):
        self.c.call("POST", "/targets", {"name": "NAS", "protocol": "smb", "host": "nas", "path": "share",
                                         "username": "u", "password": "secret-pw"})
        self.c.call("PUT", "/smtp", {"host": "smtp.example.com", "sender": "pi@example.com", "password": "smtp-pw"})
        status, body = self.c.call("POST", "/backup/export", {"passphrase": "backup-pass"})
        self.assertEqual(status, 200, body)
        backup = body["backup"]
        self.assertNotIn("secret-pw", json.dumps(backup))
        self.assertTrue(body["filename"].endswith(".json"))
        # Change things, then restore.
        tid = self.c.call("GET", "/targets")[1]["targets"][0]["id"]
        self.c.call("DELETE", f"/targets/{tid}")
        self.assertEqual(self.c.call("POST", "/backup/restore", {"backup": backup})[1]["error"], "passphrase_required")
        self.assertEqual(self.c.call("POST", "/backup/restore", {"backup": backup, "passphrase": "nope-nope"})[1]["error"],
                         "wrong_passphrase")
        status, body = self.c.call("POST", "/backup/restore", {"backup": backup, "passphrase": "backup-pass"})
        self.assertEqual(status, 200, body)
        ctx = self.svc.ctx
        row = ctx.db.one("SELECT * FROM targets WHERE name = 'NAS'")
        self.assertEqual(ctx.secrets.decrypt(row["secret"]), "secret-pw")
        self.assertEqual(ctx.secrets.decrypt(ctx.mailer.settings()["password"]), "smtp-pw")
        # Sessions are reset by a restore.
        self.assertEqual(self.c.call("GET", "/me")[0], 401)

    def test_backup_without_passphrase_drops_secrets(self):
        self.c.call("POST", "/targets", {"name": "NAS", "protocol": "local", "path": "/tmp/x", "password": "pw"})
        backup = self.c.call("POST", "/backup/export", {})[1]["backup"]
        self.assertIsNone(backup["secrets"])

    def test_scheduled_backup_upload(self):
        dest = self.svc.tmp / "backups"
        tid = self.c.call("POST", "/targets", {"name": "Local", "protocol": "local", "path": str(dest)})[1]["target"]["id"]
        status, body = self.c.call("PUT", "/backup", {"enabled": True, "target_id": tid, "directory": "cfg/pi",
                                                      "interval": "daily", "hour": 3, "passphrase": "backup-pass"})
        self.assertEqual(status, 200, body)
        self.assertTrue(body["settings"]["has_passphrase"])
        self.assertNotIn("passphrase", body["settings"])
        status, body = self.c.call("POST", "/backup/run")
        self.assertTrue(body["last"]["ok"], body)
        files = list((dest / "cfg" / "pi").glob("netusbflash-backup-*.json"))
        self.assertEqual(len(files), 1)
        self.assertIsNotNone(json.loads(files[0].read_text())["secrets"])
        self.assertIsNotNone(body["next_run"])


if __name__ == "__main__":
    unittest.main()

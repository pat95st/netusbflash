import time
import unittest
from pathlib import Path
from unittest import mock

from helpers import Client, ServiceFixture, wait_for


class SetupAndAuthTests(unittest.TestCase):
    def setUp(self):
        self.svc = ServiceFixture()
        self.c = self.svc.client

    def tearDown(self):
        self.svc.close()

    def test_setup_requires_code(self):
        status, body = self.c.call("GET", "/setup/status")
        self.assertEqual((status, body["completed"]), (200, False))
        self.c.setup_code = "AAAA-BBBB-CCCC"
        status, body = self.c.call("POST", "/setup/verify", {})
        self.assertEqual((status, body["error"]), (403, "setup_code_invalid"))

    def test_login_blocked_before_setup(self):
        status, body = self.c.call("POST", "/auth/login", {"username": "a", "password": "b"})
        self.assertEqual((status, body["error"]), (409, "setup_required"))

    def test_wizard_validation(self):
        self.c.setup_code = self.svc.ctx.setup.read_code()
        status, body = self.c.call("POST", "/setup/admin", {"username": "ad", "password": "short"})
        self.assertEqual(status, 422)
        self.assertEqual(body["fields"], {"username": "invalid", "password": "too_short"})

    def test_full_setup_then_login_and_roles(self):
        self.svc.complete_setup()
        self.assertFalse(self.svc.paths.setup_token.exists())
        status, body = self.c.call("POST", "/setup/verify", {})
        self.assertEqual(body["error"], "setup_done")

        status, body = self.c.call("POST", "/users", {"username": "bob", "role": "viewer"})
        self.assertEqual(status, 201)
        temp = body["temporary_password"]

        bob = Client(self.c.socket_path)
        status, body = bob.call("POST", "/auth/login", {"username": "bob", "password": temp})
        self.assertEqual(status, 200)
        bob.token = body["token"]
        self.assertTrue(body["user"]["must_change_pw"])
        status, body = bob.call("GET", "/targets")
        self.assertEqual(body["error"], "password_change_required")
        status, body = bob.call("POST", "/me/password", {"current": temp, "new": "another-long-pass"})
        self.assertEqual(status, 200, body)
        bob.token = body["token"]
        self.assertEqual(bob.call("GET", "/targets")[0], 200)
        status, body = bob.call("POST", "/targets", {"name": "x", "protocol": "local", "path": "/tmp/x"})
        self.assertEqual((status, body["error"]), (403, "forbidden"))
        self.assertEqual(bob.call("GET", "/users")[0], 403)

    def test_lockout(self):
        self.svc.complete_setup()
        anon = Client(self.c.socket_path)
        for _ in range(4):
            self.assertEqual(anon.call("POST", "/auth/login", {"username": "admin", "password": "nope"})[0], 401)
        status, body = anon.call("POST", "/auth/login", {"username": "admin", "password": "nope"})
        self.assertEqual((status, body["error"]), (423, "locked"))
        status, body = anon.call("POST", "/auth/login", {"username": "admin", "password": "correct-horse-battery"})
        self.assertEqual(body["error"], "locked")

    def test_last_admin_protected(self):
        self.svc.complete_setup()
        status, body = self.c.call("GET", "/me")
        uid = body["user"]["id"]
        status, body = self.c.call("PUT", f"/users/{uid}", {"role": "viewer"})
        self.assertEqual((status, body["error"]), (409, "last_admin"))
        status, body = self.c.call("DELETE", f"/users/{uid}")
        self.assertEqual(body["error"], "cannot_delete_self")


class PipelineTests(unittest.TestCase):
    """New file on the simulated stick -> spool -> upload to a local target -> email."""

    def setUp(self):
        self.svc = ServiceFixture()
        self.svc.complete_setup()
        self.dest = self.svc.tmp / "dest"
        self.sent: list = []
        patcher = mock.patch("netusbflash.mailer.Mailer.send", side_effect=self._fake_send)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.svc.start_workers()

    def _fake_send(self, recipients, subject, body, cfg=None):
        self.sent.append((recipients, subject, body))

    def tearDown(self):
        self.svc.close()

    def test_pipeline(self):
        c = self.svc.client
        status, body = c.call("POST", "/targets", {
            "name": "Archive", "protocol": "local", "path": str(self.dest),
            "options": {"subfolder": "", "keep_structure": True}})
        self.assertEqual(status, 201, body)
        tid = body["target"]["id"]
        status, body = c.call("POST", f"/targets/{tid}/test")
        self.assertTrue(body["ok"], body)

        self.assertEqual(c.call("PUT", "/smtp", {"host": "smtp.example.com", "port": 587,
                                                  "security": "starttls", "sender": "pi@example.com",
                                                  "password": "secret"})[0], 200)
        status, body = c.call("POST", "/rules", {"name": "All", "events": ["created", "uploaded"],
                                                 "recipients": "ops@example.com", "mode": "instant"})
        self.assertEqual(status, 201, body)

        # Initial scan records the empty stick as the baseline.
        stick = self.svc.paths.sim_dir
        self.assertEqual(c.call("POST", "/usb/sync")[0], 200)
        self.assertTrue(wait_for(lambda: self.svc.ctx.db.get_setting("last_sync") is not None))

        (stick / "REC").mkdir()
        (stick / "REC" / "SONG01.WAV").write_bytes(b"RIFF" + b"\0" * 1000)
        c.call("POST", "/usb/sync")

        uploaded = self.dest / "REC" / "SONG01.WAV"
        self.assertTrue(wait_for(uploaded.exists, timeout=20), "file was not uploaded")
        self.assertEqual(uploaded.stat().st_size, 1004)

        self.assertTrue(wait_for(lambda: self.sent and any("SONG01" in m[2] for m in self.sent), timeout=20))
        status, body = c.call("GET", "/files")
        self.assertTrue(wait_for(lambda: c.call("GET", "/files")[1]["files"][0]["uploaded"]))
        # Spool copy is removed after a successful upload.
        self.assertTrue(wait_for(lambda: not any(self.svc.paths.spool.iterdir())))

        status, body = c.call("GET", "/status")
        self.assertEqual(body["uploads"]["done"], 1)

    def test_failed_upload_can_be_retried(self):
        c = self.svc.client
        status, body = c.call("POST", "/targets", {"name": "Bad", "protocol": "local",
                                                   "path": "/proc/not-writable",
                                                   "options": {"subfolder": ""}})
        tid = body["target"]["id"]
        c.call("POST", "/usb/sync")
        self.assertTrue(wait_for(lambda: self.svc.ctx.db.get_setting("last_sync") is not None))
        (self.svc.paths.sim_dir / "A.WAV").write_bytes(b"x")
        c.call("POST", "/usb/sync")
        self.assertTrue(wait_for(lambda: c.call("GET", "/uploads?status=pending")[1]["uploads"]
                                 and c.call("GET", "/uploads?status=pending")[1]["uploads"][0]["attempts"] >= 1))
        upload = c.call("GET", "/uploads")[1]["uploads"][0]
        self.assertTrue(upload["last_error"])
        c.call("PUT", f"/targets/{tid}", {"name": "Good", "protocol": "local", "path": str(self.dest),
                                          "options": {"subfolder": ""}})
        self.svc.ctx.db.run("UPDATE uploads SET next_try = 0")
        self.svc.ctx.uploader.wake()
        self.assertTrue(wait_for((self.dest / "A.WAV").exists, timeout=20))


if __name__ == "__main__":
    unittest.main()

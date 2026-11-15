"""Cloud targets: Dropbox, iCloud Drive, OneDrive, Google Drive and Box."""

import base64
import json
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import ServiceFixture

from netusbflash.cloud import (CloudError, dump_secret, load_secret, normalize_token, parse_config_answer,
                               read_rclone_section)
from netusbflash.config import Paths
from netusbflash.handlers import merge_target_secret
from netusbflash.service import Context
from netusbflash.transports import RcloneTransport, TransferError, make_transport

TOKEN = {"access_token": "AT", "token_type": "Bearer", "refresh_token": "RT",
         "expiry": "2026-11-15T12:00:00Z"}
TOKEN_JSON = json.dumps(TOKEN, separators=(",", ":"))

# A stand-in for rclone. "obscure" echoes a marker; every other call finds the
# --config file, simulates a token refresh and records its arguments. The
# iCloud config state machine is simulated for "config update".
FAKE_RCLONE = r"""#!/bin/sh
conf=""
prev=""
for arg in "$@"; do
    if [ "$prev" = "--config" ]; then conf="$arg"; fi
    prev="$arg"
done
echo "$@" >> "$FAKE_LOG"
if [ "$1" = "obscure" ]; then echo "OBSCURED"; exit 0; fi
case " $* " in
  *" config update "*"--continue"*"--result 123456"*)
      printf 'trust_token = TRUST\ncookies = COOKIE\n' >> "$conf"
      echo '{"State": "", "Option": null, "Error": "", "Result": ""}'; exit 0 ;;
  *" config update "*"--continue"*)
      echo '{"State": "*2fa_do", "Option": {"Name": "config_2fa", "Help": "code"}, "Error": "invalid code"}'; exit 0 ;;
  *" config update "*)
      echo 'some log line'
      echo '{"State": "*2fa_do", "Option": {"Name": "config_2fa", "Help": "Two-factor code",'
      echo '  "Default": "", "Examples": [{"Value": "x"}]}, "Error": "", "Result": ""}'; exit 0 ;;
esac
if [ -n "$conf" ] && grep -q '^token = ' "$conf"; then
    sed -i 's/^token = .*/token = {"access_token":"NEW","refresh_token":"RT2"}/' "$conf"
fi
if [ "$FAKE_FAIL" = "1" ]; then echo "ERROR : didn't find backend called \"iclouddrive\"" >&2; exit 1; fi
case "$1" in
  lsjson) echo "[]" ;;
esac
exit 0
"""


class FakeRclone:
    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="nuf-rclone"))
        script = self.dir / "rclone"
        script.write_text(FAKE_RCLONE)
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        self.log = self.dir / "log"
        self.env = mock.patch.dict(os.environ, {"PATH": f"{self.dir}:{os.environ['PATH']}",
                                                "FAKE_LOG": str(self.log)})

    def __enter__(self):
        self.env.start()
        return self

    def __exit__(self, *exc):
        self.env.stop()
        shutil.rmtree(self.dir, ignore_errors=True)

    def calls(self) -> list[str]:
        return self.log.read_text().splitlines() if self.log.exists() else []


class TokenTests(unittest.TestCase):
    def test_raw_json(self):
        self.assertEqual(json.loads(normalize_token(json.dumps(TOKEN))), TOKEN)

    def test_paste_block(self):
        paste = ("Paste the following into your remote machine --->\n" + json.dumps(TOKEN) +
                 "\n<---End paste\n")
        self.assertEqual(json.loads(normalize_token(paste))["refresh_token"], "RT")

    def test_base64_wrapper(self):
        blob = base64.urlsafe_b64encode(json.dumps({"token": json.dumps(TOKEN)}).encode()).decode().rstrip("=")
        self.assertEqual(json.loads(normalize_token(blob))["access_token"], "AT")

    def test_unknown_fields_dropped(self):
        token = normalize_token(json.dumps({**TOKEN, "evil": "x"}))
        self.assertNotIn("evil", token)

    def test_invalid(self):
        for raw in ("", "hello", '{"foo": 1}', "x" * 20000):
            with self.assertRaises(CloudError):
                normalize_token(raw)


class SecretTests(unittest.TestCase):
    def test_roundtrip(self):
        data = {"token": TOKEN_JSON, "client_secret": "cs"}
        self.assertEqual(load_secret("dropbox", dump_secret("dropbox", data)), data)

    def test_plain_password_for_icloud(self):
        self.assertEqual(load_secret("icloud", "hunter2"), {"password": "hunter2"})

    def test_legacy_unchanged(self):
        self.assertEqual(dump_secret("smb", {"password": "pw"}), "pw")
        self.assertEqual(load_secret("smb", '{"a": 1}'), {"password": '{"a": 1}'})

    def test_merge_switch_to_icloud_keeps_password(self):
        old = {"protocol": "smb", "username": "u"}
        plain = merge_target_secret({"protocol": "icloud", "username": "a@b.c"}, {}, old, "pw")
        self.assertEqual(load_secret("icloud", plain), {"password": "pw"})

    def test_merge_new_apple_id_drops_session(self):
        old = {"protocol": "icloud", "username": "a@b.c"}
        stored = dump_secret("icloud", {"password": "pw", "trust_token": "T", "cookies": "C"})
        same = merge_target_secret({"protocol": "icloud", "username": "A@b.c"}, {}, old, stored)
        self.assertEqual(load_secret("icloud", same)["trust_token"], "T")
        other = merge_target_secret({"protocol": "icloud", "username": "x@b.c"}, {}, old, stored)
        self.assertEqual(load_secret("icloud", other), {"password": "pw"})

    def test_merge_other_oauth_provider_drops_token(self):
        old = {"protocol": "dropbox", "username": ""}
        stored = dump_secret("dropbox", {"token": TOKEN_JSON})
        self.assertEqual(merge_target_secret({"protocol": "box", "username": ""}, {}, old, stored), "")


class ConfigTests(unittest.TestCase):
    def _conf(self, protocol, secret, **target):
        base = {"name": "t", "protocol": protocol, "host": "", "port": None, "path": "Rec",
                "username": "", "options": {}}
        base.update(target)
        paths = Paths(Path("/x"), Path("/x"), Path("/x"))
        t = RcloneTransport(Context.target_view(base), dump_secret(protocol, secret), paths)
        with mock.patch.object(RcloneTransport, "_obscure", return_value="OBSCURED"):
            return read_rclone_section(t.config_text(), "target")

    def test_dropbox(self):
        conf = self._conf("dropbox", {"token": TOKEN_JSON, "client_secret": "cs"},
                          options={"client_id": "cid"})
        self.assertEqual(conf, {"type": "dropbox", "client_id": "cid", "client_secret": "cs", "token": TOKEN_JSON})

    def test_gdrive(self):
        conf = self._conf("gdrive", {"token": TOKEN_JSON}, options={"root_folder_id": "abc", "team_drive": "td"})
        self.assertEqual((conf["type"], conf["scope"], conf["root_folder_id"], conf["team_drive"]),
                         ("drive", "drive", "abc", "td"))

    def test_onedrive(self):
        conf = self._conf("onedrive", {"token": TOKEN_JSON},
                          options={"drive_id": "D1", "drive_type": "personal"})
        self.assertEqual((conf["type"], conf["drive_id"], conf["drive_type"]), ("onedrive", "D1", "personal"))

    def test_box(self):
        self.assertEqual(self._conf("box", {"token": TOKEN_JSON})["type"], "box")

    def test_icloud(self):
        conf = self._conf("icloud", {"password": "pw", "trust_token": "T", "cookies": "C"}, username="a@b.c")
        self.assertEqual(conf, {"type": "iclouddrive", "apple_id": "a@b.c", "pass": "OBSCURED",
                                "trust_token": "T", "cookies": "C"})

    def test_parse_config_answer(self):
        out = 'log\n{"State": "s", "Option": {"Name": "x", "Examples": [{"a": 1}]}, "Error": ""}\n'
        self.assertEqual(parse_config_answer(out)["Option"]["Name"], "x")
        with self.assertRaises(CloudError):
            parse_config_answer("nothing here")


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="nuf-t"))
        self.paths = Paths(self.tmp / "etc", self.tmp / "lib", self.tmp / "run")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _target(self, protocol, **options):
        return Context.target_view({"id": 7, "name": "t", "protocol": protocol, "host": "", "port": None,
                                    "path": "Rec", "username": "", "options": options})

    def test_refreshed_token_is_reported(self):
        changes = []
        with FakeRclone():
            transport = make_transport(self._target("box"), dump_secret("box", {"token": TOKEN_JSON}),
                                       self.paths, on_secret=changes.append)
            transport.test()
        self.assertEqual(changes, [{"token": '{"access_token":"NEW","refresh_token":"RT2"}'}])
        self.assertEqual(list(self.paths.run.glob("rclone-*.conf")), [])

    def test_missing_token_or_drive(self):
        with FakeRclone():
            with self.assertRaisesRegex(TransferError, "token"):
                make_transport(self._target("dropbox"), "", self.paths).test()
            secret = dump_secret("onedrive", {"token": TOKEN_JSON})
            with self.assertRaisesRegex(TransferError, "drive ID"):
                make_transport(self._target("onedrive"), secret, self.paths).test()
            with self.assertRaisesRegex(TransferError, "Sign in"):
                make_transport(self._target("icloud"), "pw", self.paths).test()

    def test_old_rclone_error(self):
        secret = dump_secret("icloud", {"password": "pw", "trust_token": "T"})
        with FakeRclone(), mock.patch.dict(os.environ, {"FAKE_FAIL": "1"}):
            with self.assertRaisesRegex(TransferError, "rclone 1.69"):
                make_transport(self._target("icloud"), secret, self.paths).test()


class CloudApiTests(unittest.TestCase):
    def setUp(self):
        self.svc = ServiceFixture()
        self.svc.complete_setup()
        self.c = self.svc.client

    def tearDown(self):
        self.svc.close()

    def _secret(self, target_id):
        row = self.svc.ctx.db.one("SELECT protocol, secret FROM targets WHERE id = ?", (target_id,))
        return load_secret(row["protocol"], self.svc.ctx.secrets.decrypt(row["secret"]))

    def test_dropbox_target(self):
        status, body = self.c.call("POST", "/targets", {"name": "db", "protocol": "dropbox", "path": "Rec"})
        self.assertEqual((status, body["fields"]), (422, {"token": "required"}))
        status, body = self.c.call("POST", "/targets", {"name": "db", "protocol": "dropbox", "path": "Rec",
                                                        "token": "garbage"})
        self.assertEqual(body["fields"], {"token": "invalid"})
        status, body = self.c.call("POST", "/targets", {
            "name": "db", "protocol": "dropbox", "path": "Rec", "host": "ignored", "port": 99,
            "token": json.dumps(TOKEN), "client_secret": "cs", "options": {"client_id": "cid"}})
        self.assertEqual(status, 201, body)
        target = body["target"]
        self.assertEqual((target["host"], target["port"]), ("", None))
        self.assertTrue(target["has_token"] and target["has_client_secret"])
        self.assertNotIn("AT", json.dumps(target))
        # Saving without a new token keeps the stored one.
        status, body = self.c.call("PUT", f"/targets/{target['id']}", {
            "name": "db2", "protocol": "dropbox", "path": "Rec2", "options": {"client_id": "cid"}})
        self.assertEqual(status, 200, body)
        self.assertEqual(self._secret(target["id"]), {"token": TOKEN_JSON, "client_secret": "cs"})

    def test_saved_test_persists_refreshed_token(self):
        status, body = self.c.call("POST", "/targets", {"name": "g", "protocol": "gdrive",
                                                        "token": json.dumps(TOKEN)})
        tid = body["target"]["id"]
        with FakeRclone():
            status, body = self.c.call("POST", f"/targets/{tid}/test", {})
        self.assertTrue(body["ok"], body)
        self.assertEqual(json.loads(self._secret(tid)["token"])["access_token"], "NEW")

    def test_onedrive_detects_drive(self):
        with mock.patch("netusbflash.handlers.detect_onedrive_drive", return_value=("DRIVE", "business")):
            status, body = self.c.call("POST", "/targets", {"name": "od", "protocol": "onedrive",
                                                            "token": json.dumps(TOKEN)})
        self.assertEqual(status, 201, body)
        self.assertEqual((body["target"]["options"]["drive_id"], body["target"]["options"]["drive_type"]),
                         ("DRIVE", "business"))
        with mock.patch("netusbflash.handlers.detect_onedrive_drive", side_effect=CloudError("expired")):
            status, body = self.c.call("POST", "/targets", {"name": "od", "protocol": "onedrive",
                                                            "token": json.dumps(TOKEN)})
        self.assertEqual((status, body["fields"]), (422, {"options.drive_id": "detect_failed"}))

    def test_icloud_login_with_2fa(self):
        status, body = self.c.call("POST", "/targets", {"name": "ic", "protocol": "icloud",
                                                        "username": "me@example.com"})
        self.assertEqual(body["fields"], {"password": "required"})
        status, body = self.c.call("POST", "/targets", {"name": "ic", "protocol": "icloud", "path": "Rec",
                                                        "username": "me@example.com", "password": "pw"})
        self.assertEqual(status, 201, body)
        tid = body["target"]["id"]
        self.assertFalse(body["target"]["icloud_signed_in"])
        self.assertEqual(self.c.call("POST", f"/targets/{tid}/icloud/code", {"code": "12"})[0], 422)
        with FakeRclone() as fake:
            status, body = self.c.call("POST", f"/targets/{tid}/icloud/login", {})
            self.assertEqual((status, body), (200, {"status": "code_required"}))
            self.assertTrue(any("config update target apple_id me@example.com" in c for c in fake.calls()))
            status, body = self.c.call("POST", f"/targets/{tid}/icloud/code", {"code": "000000"})
            self.assertEqual((status, body["error"]), (502, "icloud_failed"))
            # A wrong code ends the attempt; start again.
            self.c.call("POST", f"/targets/{tid}/icloud/login", {})
            status, body = self.c.call("POST", f"/targets/{tid}/icloud/code", {"code": "123456"})
            self.assertEqual((status, body), (200, {"status": "ok"}))
        self.assertEqual(self._secret(tid), {"password": "pw", "trust_token": "TRUST", "cookies": "COOKIE"})
        self.assertEqual(list(self.svc.paths.run.glob("icloud-login-*")), [])
        status, body = self.c.call("GET", f"/targets/{tid}")
        self.assertTrue(body["target"]["icloud_signed_in"])
        self.assertNotIn("TRUST", json.dumps(body))
        # A new password needs a new sign-in.
        self.c.call("PUT", f"/targets/{tid}", {"name": "ic", "protocol": "icloud", "path": "Rec",
                                               "username": "me@example.com", "password": "pw2"})
        self.assertEqual(self._secret(tid), {"password": "pw2"})

    def test_icloud_endpoints_need_icloud_target(self):
        status, body = self.c.call("POST", "/targets", {"name": "l", "protocol": "local", "path": "/tmp/x"})
        status, body = self.c.call("POST", f"/targets/{body['target']['id']}/icloud/login", {})
        self.assertEqual((status, body["error"]), (400, "not_icloud"))


if __name__ == "__main__":
    unittest.main()

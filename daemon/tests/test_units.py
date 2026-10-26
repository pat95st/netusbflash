import tempfile
import unittest
from pathlib import Path

from netusbflash.auth import hash_password, verify_password
from netusbflash.gadget import mbr_first_partition_at_2048
from netusbflash.monitor import diff_index, matches, walk_files
from netusbflash.setup import generate_code, normalise_code
from netusbflash.transports import join_remote, remote_relative, render_subfolder
from netusbflash.uploader import backoff
from netusbflash.validate import ValidationError, Validator


class PasswordTests(unittest.TestCase):
    def test_hash_roundtrip(self):
        stored = hash_password("a long passphrase")
        self.assertTrue(verify_password("a long passphrase", stored))
        self.assertFalse(verify_password("wrong", stored))
        self.assertFalse(verify_password("x", "garbage"))

    def test_hashes_are_salted(self):
        self.assertNotEqual(hash_password("same"), hash_password("same"))


class SetupCodeTests(unittest.TestCase):
    def test_format_and_normalise(self):
        code = generate_code()
        self.assertRegex(code, r"^[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}$")
        self.assertEqual(normalise_code(code.lower().replace("-", " ")), code)


class ScanTests(unittest.TestCase):
    def test_walk_ignores_system_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "REC").mkdir()
            (root / "REC" / "TRACK01.WAV").write_bytes(b"x" * 10)
            (root / "._TRACK01.WAV").write_bytes(b"x")
            (root / ".DS_Store").write_bytes(b"x")
            (root / "System Volume Information").mkdir()
            (root / "System Volume Information" / "IndexerVolumeGuid").write_bytes(b"x")
            files = walk_files(root)
            self.assertEqual(list(files), ["REC/TRACK01.WAV"])
            self.assertEqual(files["REC/TRACK01.WAV"][0], 10)

    def test_diff(self):
        known = {"a.wav": {"size": 1, "mtime": 1.0}, "b.wav": {"size": 2, "mtime": 2.0},
                 "c.wav": {"size": 3, "mtime": 3.0}}
        current = {"a.wav": (1, 1.0), "b.wav": (5, 2.0), "d.wav": (4, 4.0)}
        created, modified, deleted = diff_index(current, known)
        self.assertEqual((created, modified, deleted), (["d.wav"], ["b.wav"], ["c.wav"]))

    def test_matches(self):
        self.assertTrue(matches("REC/A.WAV", "*.wav, *.mp3", ""))
        self.assertFalse(matches("REC/A.TXT", "*.wav", ""))
        self.assertFalse(matches("REC/A.WAV", "*", "a.*"))
        self.assertTrue(matches("x.bin", "", ""))


class RemotePathTests(unittest.TestCase):
    def test_join(self):
        self.assertEqual(join_remote("/upload", "2026", "a.wav"), "/upload/2026/a.wav")
        self.assertEqual(join_remote("share/dir/", "", "a.wav"), "share/dir/a.wav")
        self.assertEqual(join_remote("", "a.wav"), "a.wav")

    def test_template(self):
        when = 1793000000.0
        self.assertRegex(render_subfolder("{year}/{date}", when, "pi"), r"^\d{4}/\d{4}-\d{2}-\d{2}$")
        self.assertEqual(render_subfolder("{hostname}", when, "pi"), "pi")

    def test_remote_relative(self):
        target = {"options": {"subfolder": "", "keep_structure": False}}
        self.assertEqual(remote_relative(target, "REC/A.WAV", 0, "pi"), "A.WAV")
        target = {"options": {"subfolder": "{hostname}", "keep_structure": True}}
        self.assertEqual(remote_relative(target, "REC/A.WAV", 0, "pi"), "pi/REC/A.WAV")


class ImageTests(unittest.TestCase):
    def test_mbr_detection(self):
        mbr = bytearray(512)
        mbr[0x1C2] = 0x07
        mbr[0x1C6:0x1CA] = (2048).to_bytes(4, "little")
        mbr[510:512] = b"\x55\xaa"
        self.assertTrue(mbr_first_partition_at_2048(bytes(mbr)))
        fat = bytearray(mbr)
        fat[3:11] = b"mkfs.fat"
        self.assertFalse(mbr_first_partition_at_2048(bytes(fat)))
        self.assertFalse(mbr_first_partition_at_2048(bytes(512)))


class MiscTests(unittest.TestCase):
    def test_backoff(self):
        self.assertEqual(backoff(1), 60)
        self.assertEqual(backoff(2), 120)
        self.assertEqual(backoff(20), 1800)

    def test_validator(self):
        v = Validator({"name": "x\n", "port": "70000", "mail": "a@b.de"})
        v.string("name")
        v.integer("port", minimum=1, maximum=65535)
        v.email("mail")
        with self.assertRaises(ValidationError) as cm:
            v.raise_if_errors()
        self.assertEqual(cm.exception.fields, {"name": "invalid", "port": "out_of_range"})


class RcloneConfigTests(unittest.TestCase):
    def _conf(self, **target):
        from unittest import mock
        from netusbflash.config import Paths
        from netusbflash.service import Context
        from netusbflash.transports import RcloneTransport
        base = {"name": "t", "host": "nas.local", "port": None, "path": "share/rec", "username": "u",
                "options": {}}
        base.update(target)
        paths = Paths(Path("/x"), Path("/x"), Path("/x"))
        t = RcloneTransport(Context.target_view(base), "pw", paths)
        with mock.patch.object(RcloneTransport, "_obscure", return_value="OBSCURED"):
            return t.config_text()

    def test_smb(self):
        conf = self._conf(protocol="smb", options={"domain": "WORK"})
        self.assertIn("type = smb", conf)
        self.assertIn("port = 445", conf)
        self.assertIn("pass = OBSCURED", conf)
        self.assertIn("domain = WORK", conf)

    def test_nextcloud(self):
        conf = self._conf(protocol="webdav", host="https://cloud.example.com/remote.php/dav/files/u",
                          options={"vendor": "nextcloud"})
        self.assertIn("url = https://cloud.example.com/remote.php/dav/files/u", conf)
        self.assertIn("vendor = nextcloud", conf)

    def test_ftps_implicit(self):
        conf = self._conf(protocol="ftps", options={"tls_mode": "implicit", "insecure_tls": True})
        self.assertIn("type = ftp", conf)
        self.assertIn("tls = true", conf)
        self.assertIn("no_check_certificate = true", conf)

    def test_sftp_key(self):
        conf = self._conf(protocol="sshfs", options={"auth": "key"})
        self.assertIn("type = sftp", conf)
        self.assertIn("key_file = /x/ssh/id_ed25519", conf)
        self.assertNotIn("pass =", conf)


if __name__ == "__main__":
    unittest.main()

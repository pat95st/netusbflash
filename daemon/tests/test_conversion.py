"""Tests for converting recordings before the upload."""

import math
import shutil
import struct
import unittest
import wave
from pathlib import Path
from unittest import mock

from helpers import ServiceFixture, wait_for

from netusbflash.converter import (DEFAULT_RULE, ffmpeg_args, output_name, output_path, parse_extensions,
                                   parse_settings)
from netusbflash.system import CommandError
from netusbflash.validate import ValidationError

HAVE_FFMPEG = shutil.which("ffmpeg") is not None


def write_wav(path: Path, seconds: float = 0.5, rate: int = 48000, channels: int = 2) -> None:
    frames = int(seconds * rate)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        data = b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate))) * channels
                        for i in range(frames))
        w.writeframes(data)


def rule(**kw):
    return {**DEFAULT_RULE, **kw}


class ConversionUnitTests(unittest.TestCase):
    def test_parse_extensions(self):
        self.assertEqual(parse_extensions("*.WAV, .aif; aiff wav"), ["wav", "aif", "aiff"])
        self.assertEqual(parse_extensions(["WAV", "flac"]), ["wav", "flac"])

    def test_output_names(self):
        self.assertEqual(output_name("SONG01.WAV", "flac"), "SONG01.FLAC")
        self.assertEqual(output_name("take.wav", "aac"), "take.m4a")
        self.assertEqual(output_name("a.b.wav", "mp3"), "a.b.mp3")
        self.assertEqual(output_path("REC/2026/x.wav", "mp3"), "REC/2026/x.mp3")

    def test_settings_validation(self):
        cfg = parse_settings({"enabled": True, "rules": [
            {"extensions": "wav, aiff", "format": "mp3", "bitrate": 256, "sample_rate": 44100, "channels": 2}]})
        self.assertEqual(cfg["rules"][0]["extensions"], ["wav", "aiff"])
        self.assertEqual(cfg["rules"][0]["bitrate"], 256)

        cases = [
            ({"extensions": "", "format": "flac"}, "rules.0.extensions"),
            ({"extensions": "wav", "format": "ogg"}, "rules.0.format"),
            ({"extensions": "wav", "format": "mp3", "bitrate": 999}, "rules.0.bitrate"),
            ({"extensions": "wav", "format": "mp3", "sample_rate": 96000}, "rules.0.sample_rate"),
            ({"extensions": "wav", "format": "flac", "sample_rate": 12345}, "rules.0.sample_rate"),
            ({"extensions": "wav", "format": "flac", "bit_depth": 8}, "rules.0.bit_depth"),
            ({"extensions": "mp3", "format": "mp3", "keep_original": True}, "rules.0.keep_original"),
            ({"extensions": "w/v", "format": "flac"}, "rules.0.extensions"),
        ]
        for body, field in cases:
            with self.assertRaises(ValidationError) as ctx:
                parse_settings({"enabled": True, "rules": [body]})
            self.assertIn(field, ctx.exception.fields, body)

        with self.assertRaises(ValidationError) as ctx:
            parse_settings({"rules": [{"extensions": "wav"}, {"extensions": "WAV,aif"}]})
        self.assertIn("rules.1.extensions", ctx.exception.fields)
        # A disabled rule may repeat an extension.
        parse_settings({"rules": [{"extensions": "wav"}, {"extensions": "wav", "enabled": False}]})
        with self.assertRaises(ValidationError) as ctx:
            parse_settings({"enabled": True, "rules": []})
        self.assertIn("rules", ctx.exception.fields)

    def test_ffmpeg_arguments(self):
        src, dest = Path("/s/in.wav"), Path("/s/out.part")
        args = ffmpeg_args(src, dest, rule(format="mp3", bitrate=320, sample_rate=44100, channels=1))
        self.assertIn("libmp3lame", args)
        self.assertEqual(args[args.index("-b:a") + 1], "320k")
        self.assertEqual(args[args.index("-ar") + 1], "44100")
        self.assertEqual(args[args.index("-ac") + 1], "1")
        self.assertEqual(args[-3:], ["-f", "mp3", str(dest)])
        args = ffmpeg_args(src, dest, rule(format="mp3", mp3_mode="vbr", vbr_quality=0))
        self.assertEqual(args[args.index("-q:a") + 1], "0")
        self.assertNotIn("-b:a", args)
        args = ffmpeg_args(src, dest, rule(format="flac", flac_level=8, bit_depth=16))
        self.assertEqual(args[args.index("-compression_level") + 1], "8")
        self.assertEqual(args[args.index("-sample_fmt") + 1], "s16")
        self.assertNotIn("-ar", args)
        args = ffmpeg_args(src, dest, rule(format="aac", bitrate=128))
        self.assertEqual(args[args.index("-c:a") + 1], "aac")
        self.assertEqual(args[-3:-1], ["-f", "ipod"])


class ConversionApiTests(unittest.TestCase):
    def setUp(self):
        self.svc = ServiceFixture()
        self.svc.complete_setup()

    def tearDown(self):
        self.svc.close()

    def test_get_and_put(self):
        c = self.svc.client
        status, body = c.call("GET", "/conversion")
        self.assertEqual(status, 200)
        self.assertFalse(body["settings"]["enabled"])
        self.assertIn("flac", body["choices"]["formats"])
        status, body = c.call("PUT", "/conversion", {"enabled": True, "rules": [
            {"extensions": "wav", "format": "aac", "bitrate": 192}]})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["settings"]["rules"][0]["format"], "aac")
        status, body = c.call("PUT", "/conversion", {"enabled": True, "rules": [
            {"extensions": "wav", "format": "mp3", "bitrate": 7}]})
        self.assertEqual(status, 422, body)


class ConversionPipelineTests(unittest.TestCase):
    def setUp(self):
        self.svc = ServiceFixture()
        self.svc.complete_setup()
        self.dest = self.svc.tmp / "dest"
        patcher = mock.patch("netusbflash.mailer.Mailer.send")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.svc.start_workers()
        c = self.svc.client
        status, body = c.call("POST", "/targets", {"name": "Archive", "protocol": "local", "path": str(self.dest),
                                                   "options": {"subfolder": "", "keep_structure": True}})
        self.assertEqual(status, 201, body)
        c.call("POST", "/usb/sync")
        self.assertTrue(wait_for(lambda: self.svc.ctx.db.get_setting("last_sync") is not None))

    def tearDown(self):
        self.svc.close()

    def configure(self, **kw):
        status, body = self.svc.client.call("PUT", "/conversion", {"enabled": True, "rules": [
            {"extensions": "wav", **kw}]})
        self.assertEqual(status, 200, body)

    def record(self, name="SONG01.WAV"):
        stick = self.svc.paths.sim_dir
        (stick / "REC").mkdir(exist_ok=True)
        write_wav(stick / "REC" / name)
        self.svc.client.call("POST", "/usb/sync")

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_wav_is_converted_to_mp3(self):
        self.configure(format="mp3", bitrate=128, sample_rate=44100, channels=1)
        self.record()
        out = self.dest / "REC" / "SONG01.MP3"
        self.assertTrue(wait_for(out.exists, timeout=30), "converted file was not uploaded")
        self.assertFalse((self.dest / "REC" / "SONG01.WAV").exists())
        head = out.read_bytes()[:3]
        self.assertTrue(head == b"ID3" or head[0] == 0xFF, head)
        # The spool copy (original and converted) is removed afterwards.
        self.assertTrue(wait_for(lambda: not any(self.svc.paths.spool.iterdir())))
        # The file on the stick is unchanged.
        self.assertTrue((self.svc.paths.sim_dir / "REC" / "SONG01.WAV").exists())

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_keep_original_uploads_both(self):
        self.configure(format="flac", flac_level=5, keep_original=True)
        self.record("take.wav")
        flac = self.dest / "REC" / "take.flac"
        wav = self.dest / "REC" / "take.wav"
        self.assertTrue(wait_for(lambda: flac.exists() and wav.exists(), timeout=30))
        self.assertEqual(flac.read_bytes()[:4], b"fLaC")

    def test_failed_conversion_uploads_original(self):
        self.configure(format="aac", bitrate=192)
        with mock.patch("netusbflash.converter.Converter.available", return_value=True), \
                mock.patch("netusbflash.converter.system.run",
                           side_effect=CommandError(["ffmpeg"], 1, "broken")):
            self.record()
            original = self.dest / "REC" / "SONG01.WAV"
            self.assertTrue(wait_for(original.exists, timeout=30), "original was not uploaded")
        self.assertFalse((self.dest / "REC" / "SONG01.M4A").exists())
        messages = [r["message"] for r in self.svc.ctx.db.all("SELECT message FROM events WHERE source = 'convert'")]
        self.assertTrue(any("uploading the original" in m for m in messages), messages)

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_failed_conversion_with_original_can_be_retried(self):
        self.configure(format="flac", keep_original=True)
        with mock.patch("netusbflash.converter.system.run", side_effect=CommandError(["ffmpeg"], 1, "broken")):
            self.record()
            self.assertTrue(wait_for((self.dest / "REC" / "SONG01.WAV").exists, timeout=30))
            c = self.svc.client
            self.assertTrue(wait_for(lambda: c.call("GET", "/uploads?status=failed")[1]["uploads"], timeout=30))
        failed = c.call("GET", "/uploads?status=failed")[1]["uploads"][0]
        self.assertIn("Conversion failed", failed["last_error"])
        self.assertEqual(c.call("POST", "/uploads/retry-failed")[0], 200)
        self.assertTrue(wait_for((self.dest / "REC" / "SONG01.FLAC").exists, timeout=30))

    def test_without_ffmpeg_files_upload_unchanged(self):
        self.configure(format="flac")
        with mock.patch("netusbflash.converter.Converter.available", return_value=False):
            self.record()
            self.assertTrue(wait_for((self.dest / "REC" / "SONG01.WAV").exists, timeout=30))


if __name__ == "__main__":
    unittest.main()

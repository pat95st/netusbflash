"""Converts audio recordings with ffmpeg before they are uploaded.

Conversion rules map source file types (by extension, e.g. "wav, aif") to an
output format (FLAC, MP3 or AAC) with its encoder settings. The first enabled
rule whose extensions match a new recording is used.

Flow: the monitor copies a new recording to the spool directory as usual. If a
rule matches, the file event is marked ``convert_status = 'pending'`` and the
upload rows point at the converted file (``uploads.local_name``). The
uploader skips events whose conversion is still pending. This worker converts
the spool copy into ``<spool dir>/converted/`` and releases the uploads.

If a conversion fails, the recording is never lost: without "keep original"
the original file is uploaded instead; with "keep original" the original is
uploaded anyway and the uploads of the converted file are marked as failed
(retrying them converts again).
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import system
from .system import CommandError
from .validate import Validator

if TYPE_CHECKING:
    from .service import Context

log = logging.getLogger(__name__)

FORMATS = ("flac", "mp3", "aac")
# Output file extension and ffmpeg muxer per format. AAC is stored in an
# MPEG-4 container (.m4a), which every player understands.
EXTENSIONS = {"flac": "flac", "mp3": "mp3", "aac": "m4a"}
MUXERS = {"flac": "flac", "mp3": "mp3", "aac": "ipod"}
# Source extensions that already are the output format (re-encoding them with
# "keep original" would give both files the same name).
SAME_FORMAT = {"flac": {"flac"}, "mp3": {"mp3"}, "aac": {"m4a", "aac", "mp4"}}

MP3_BITRATES = (32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320)
AAC_BITRATES = (32, 48, 64, 96, 128, 160, 192, 224, 256, 320, 384, 448, 512)
SAMPLE_RATES = (0, 8000, 11025, 16000, 22050, 24000, 32000, 44100, 48000, 88200, 96000, 176400, 192000)
MAX_SAMPLE_RATE = {"flac": 192000, "mp3": 48000, "aac": 96000}
BIT_DEPTHS = (0, 16, 24)
CHANNELS = (0, 1, 2)
MP3_MODES = ("cbr", "vbr")
MAX_RULES = 20
EXTENSION_RE = re.compile(r"^[a-z0-9]{1,10}$")

DEFAULT_CONVERSION: dict[str, Any] = {"enabled": False, "rules": []}
DEFAULT_RULE: dict[str, Any] = {
    "enabled": True,
    "extensions": ["wav"],
    "format": "flac",
    "bitrate": 192,
    "mp3_mode": "cbr",
    "vbr_quality": 2,
    "flac_level": 5,
    "bit_depth": 0,
    "sample_rate": 0,
    "channels": 0,
    "keep_original": False,
}

# A long recording on a Raspberry Pi Zero 2 can take a while.
TIMEOUT = 6 * 3600


class ConversionError(Exception):
    pass


def parse_extensions(raw: Any) -> list[str]:
    """'*.WAV, .aif; aiff' -> ['wav', 'aif', 'aiff']"""
    if isinstance(raw, list):
        items = [str(x) for x in raw]
    else:
        items = re.split(r"[,;\s]+", str(raw or ""))
    result: list[str] = []
    for item in items:
        ext = item.strip().lower()
        if ext.startswith("*"):
            ext = ext[1:]
        ext = ext.lstrip(".")
        if ext and ext not in result:
            result.append(ext)
    return result


def parse_rule(body: Any) -> tuple[dict[str, Any], dict[str, str]]:
    """Validate one rule. Returns (rule, field errors)."""
    if not isinstance(body, dict):
        return dict(DEFAULT_RULE), {"rule": "invalid"}
    v = Validator(body)
    errors = v.errors
    extensions = parse_extensions(body.get("extensions"))
    if not extensions:
        errors["extensions"] = "required"
    elif len(extensions) > 20 or any(not EXTENSION_RE.match(e) for e in extensions):
        errors["extensions"] = "invalid"
    fmt = v.choice("format", FORMATS, "flac")
    mp3_mode = v.choice("mp3_mode", MP3_MODES, "cbr")
    bitrate = v.integer("bitrate", minimum=32, maximum=512, default=DEFAULT_RULE["bitrate"])
    allowed = MP3_BITRATES if fmt == "mp3" else AAC_BITRATES
    if fmt in ("mp3", "aac") and bitrate not in allowed:
        errors["bitrate"] = "invalid"
    vbr_quality = v.integer("vbr_quality", minimum=0, maximum=9, default=DEFAULT_RULE["vbr_quality"])
    flac_level = v.integer("flac_level", minimum=0, maximum=8, default=DEFAULT_RULE["flac_level"])
    bit_depth = v.integer("bit_depth", minimum=0, maximum=32, default=0)
    if bit_depth not in BIT_DEPTHS:
        errors["bit_depth"] = "invalid"
    sample_rate = v.integer("sample_rate", minimum=0, maximum=192000, default=0)
    if sample_rate not in SAMPLE_RATES:
        errors["sample_rate"] = "invalid"
    elif sample_rate > MAX_SAMPLE_RATE[fmt]:
        errors["sample_rate"] = "unsupported"
    channels = v.integer("channels", minimum=0, maximum=2, default=0)
    keep_original = v.boolean("keep_original", False)
    if keep_original and set(extensions) & SAME_FORMAT[fmt]:
        errors["keep_original"] = "same_format"
    rule = {
        "enabled": v.boolean("enabled", True),
        "extensions": extensions,
        "format": fmt,
        "bitrate": bitrate if bitrate is not None else DEFAULT_RULE["bitrate"],
        "mp3_mode": mp3_mode,
        "vbr_quality": vbr_quality if vbr_quality is not None else DEFAULT_RULE["vbr_quality"],
        "flac_level": flac_level if flac_level is not None else DEFAULT_RULE["flac_level"],
        "bit_depth": bit_depth or 0,
        "sample_rate": sample_rate or 0,
        "channels": channels or 0,
        "keep_original": keep_original,
    }
    return rule, errors


def parse_settings(body: dict[str, Any]) -> dict[str, Any]:
    """Validate the whole conversion configuration (raises ValidationError)."""
    v = Validator(body)
    enabled = v.boolean("enabled", False)
    raw_rules = body.get("rules") or []
    if not isinstance(raw_rules, list):
        v.errors["rules"] = "invalid"
        raw_rules = []
    if len(raw_rules) > MAX_RULES:
        v.errors["rules"] = "too_many"
    rules = []
    seen: dict[str, int] = {}
    for index, raw in enumerate(raw_rules[:MAX_RULES]):
        rule, errors = parse_rule(raw)
        if rule["enabled"] and "extensions" not in errors:
            for ext in rule["extensions"]:
                if ext in seen:
                    errors["extensions"] = "duplicate"
                seen.setdefault(ext, index)
        for field, error in errors.items():
            v.errors[f"rules.{index}.{field}"] = error
        rules.append(rule)
    if enabled and not any(r["enabled"] for r in rules):
        v.errors["rules"] = "required"
    v.raise_if_errors()
    return {"enabled": enabled, "rules": rules}


def output_name(name: str, fmt: str) -> str:
    """'SONG01.WAV' -> 'SONG01.FLAC' (keeps upper case), 'take.wav' -> 'take.flac'."""
    stem, dot, suffix = name.rpartition(".")
    if not dot or not stem:
        stem, suffix = name, ""
    ext = EXTENSIONS[fmt]
    if suffix and suffix.isupper():
        ext = ext.upper()
    return f"{stem}.{ext}"


def output_path(usb_path: str, fmt: str) -> str:
    folder, slash, name = usb_path.rpartition("/")
    return f"{folder}{slash}{output_name(name, fmt)}"


def ffmpeg_args(src: Path, dest: Path, rule: dict[str, Any]) -> list[str]:
    fmt = rule["format"]
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
           "-i", str(src), "-map", "0:a:0", "-map_metadata", "0", "-vn"]
    if fmt == "flac":
        cmd += ["-c:a", "flac", "-compression_level", str(rule["flac_level"])]
        if rule["bit_depth"] == 16:
            cmd += ["-sample_fmt", "s16"]
        elif rule["bit_depth"] == 24:
            cmd += ["-sample_fmt", "s32", "-bits_per_raw_sample", "24"]
    elif fmt == "mp3":
        cmd += ["-c:a", "libmp3lame"]
        if rule["mp3_mode"] == "vbr":
            cmd += ["-q:a", str(rule["vbr_quality"])]
        else:
            cmd += ["-b:a", f"{rule['bitrate']}k"]
        cmd += ["-id3v2_version", "3"]
    else:
        cmd += ["-c:a", "aac", "-b:a", f"{rule['bitrate']}k", "-movflags", "+faststart"]
    if rule["sample_rate"]:
        cmd += ["-ar", str(rule["sample_rate"])]
    if rule["channels"]:
        cmd += ["-ac", str(rule["channels"])]
    cmd += ["-f", MUXERS[fmt], str(dest)]
    if system.which("nice"):
        cmd = ["nice", "-n", "10"] + cmd
    return cmd


def describe(rule: dict[str, Any]) -> str:
    """Short human-readable summary for log messages, e.g. 'MP3 192 kbit/s'."""
    fmt = rule["format"]
    if fmt == "flac":
        text = f"FLAC level {rule['flac_level']}"
        if rule["bit_depth"]:
            text += f", {rule['bit_depth']} bit"
    elif fmt == "mp3" and rule["mp3_mode"] == "vbr":
        text = f"MP3 VBR V{rule['vbr_quality']}"
    else:
        text = f"{fmt.upper()} {rule['bitrate']} kbit/s"
    if rule["sample_rate"]:
        text += f", {rule['sample_rate']} Hz"
    if rule["channels"]:
        text += ", mono" if rule["channels"] == 1 else ", stereo"
    return text


class Converter(threading.Thread):
    def __init__(self, ctx: "Context"):
        super().__init__(name="converter", daemon=True)
        self.ctx = ctx
        self.stop_event = threading.Event()
        self._wake = threading.Event()
        self.current: dict[str, Any] | None = None
        self._warned_missing = False

    # Configuration ---------------------------------------------------------

    def settings(self) -> dict[str, Any]:
        return self.ctx.db.get_dict_setting("conversion", DEFAULT_CONVERSION)

    @staticmethod
    def available() -> bool:
        return system.which("ffmpeg")

    @staticmethod
    def ffmpeg_version() -> str:
        try:
            first = system.run(["ffmpeg", "-hide_banner", "-version"], timeout=10).splitlines()[0]
        except (CommandError, IndexError):
            return ""
        match = re.match(r"ffmpeg version (\S+)", first)
        return match.group(1) if match else first[:60]

    def rule_for(self, usb_path: str) -> dict[str, Any] | None:
        """The conversion rule for a new recording, or None."""
        cfg = self.settings()
        if not cfg["enabled"]:
            return None
        name = usb_path.rsplit("/", 1)[-1]
        if "." not in name:
            return None
        ext = name.rsplit(".", 1)[-1].lower()
        for raw in cfg["rules"]:
            rule = {**DEFAULT_RULE, **raw}
            if rule["enabled"] and ext in rule["extensions"]:
                if not self.available():
                    if not self._warned_missing:
                        self._warned_missing = True
                        self.ctx.db.log("error", "convert",
                                        "ffmpeg is not installed: recordings are uploaded without conversion "
                                        "(sudo apt install ffmpeg)")
                    return None
                self._warned_missing = False
                return rule
        return None

    def queue_info(self) -> dict[str, Any]:
        pending = self.ctx.db.scalar("SELECT COUNT(*) FROM file_events WHERE convert_status = 'pending'") or 0
        return {"pending": pending, "current": self.current}

    # Worker ----------------------------------------------------------------

    def wake(self) -> None:
        self._wake.set()

    def stop(self) -> None:
        self.stop_event.set()
        self._wake.set()

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                worked = self.process_next()
            except Exception as exc:
                log.exception("conversion failed")
                self.ctx.db.log("error", "convert", f"Converter error: {exc}")
                worked = False
            if not worked:
                self._wake.wait(15)
                self._wake.clear()

    def process_next(self) -> bool:
        event = self.ctx.db.one("SELECT * FROM file_events WHERE convert_status = 'pending' ORDER BY id LIMIT 1")
        if event is None:
            return False
        self.convert_event(event)
        return True

    def convert_event(self, event: dict[str, Any]) -> None:
        db = self.ctx.db
        try:
            rule = {**DEFAULT_RULE, **json.loads(event["convert_options"] or "{}")}
        except json.JSONDecodeError:
            rule = dict(DEFAULT_RULE)
        src = Path(event["spool_path"] or "")
        dest_name = output_name(src.name, rule["format"])
        dest = src.parent / "converted" / dest_name
        self.current = {"event_id": event["id"], "path": event["path"], "format": rule["format"],
                        "started": time.time()}
        started = time.time()
        try:
            self._convert(src, dest, rule)
        except ConversionError as exc:
            self.current = None
            self._failed(event, rule, str(exc))
            return
        self.current = None
        db.run("UPDATE file_events SET convert_status = 'done' WHERE id = ?", (event["id"],))
        original_needed = db.scalar("SELECT COUNT(*) FROM uploads WHERE event_id = ? AND local_name = '' "
                                    "AND status IN ('pending', 'failed')", (event["id"],))
        if not original_needed:
            src.unlink(missing_ok=True)
        db.log("info", "convert",
               f"Converted {event['path']} to {dest_name} ({describe(rule)}, "
               f"{_size(dest.stat().st_size)} in {time.time() - started:.0f} s)")
        self.ctx.uploader.wake()

    def _convert(self, src: Path, dest: Path, rule: dict[str, Any]) -> None:
        if not src.exists():
            raise ConversionError("Local copy is missing")
        if not self.available():
            raise ConversionError("ffmpeg is not installed")
        dest.parent.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(dest.parent).free
        if free - src.stat().st_size < 256 * 1024 * 1024:
            raise ConversionError("Not enough free space for the converted file")
        part = dest.with_name(dest.name + ".part")
        try:
            system.run(ffmpeg_args(src, part, rule), timeout=TIMEOUT)
            if not part.exists() or part.stat().st_size == 0:
                raise ConversionError("ffmpeg did not produce an output file")
            part.replace(dest)
        except CommandError as exc:
            raise ConversionError(f"ffmpeg failed: {exc.output[-300:] or exc}") from exc
        finally:
            part.unlink(missing_ok=True)

    def _failed(self, event: dict[str, Any], rule: dict[str, Any], message: str) -> None:
        db = self.ctx.db
        db.run("UPDATE file_events SET convert_status = 'failed' WHERE id = ?", (event["id"],))
        rows = db.all("SELECT u.*, e.path AS usb_path FROM uploads u JOIN file_events e ON e.id = u.event_id "
                      "WHERE u.event_id = ? AND u.local_name != '' AND u.status = 'pending'", (event["id"],))
        if rule["keep_original"]:
            db.log("error", "convert", f"Could not convert {event['path']}: {message}")
            for row in rows:
                target = db.one("SELECT * FROM targets WHERE id = ?", (row["target_id"],))
                if target is not None:
                    self.ctx.uploader._fail(row, target, f"Conversion failed: {message}", final=True)
        else:
            # Never lose a recording: upload the original instead.
            original = Path(event["spool_path"] or "").name
            converted = output_name(original, rule["format"])
            for row in rows:
                remote = row["remote_path"]
                if remote.endswith(converted):
                    remote = remote[: len(remote) - len(converted)] + original
                db.run("UPDATE uploads SET local_name = '', remote_path = ? WHERE id = ?", (remote, row["id"]))
            db.log("error", "convert",
                   f"Could not convert {event['path']}, uploading the original file instead: {message}")
        self.ctx.uploader.wake()

    def retry(self, event_id: int) -> None:
        """Convert again (used when failed uploads of a converted file are retried)."""
        self.ctx.db.run("UPDATE file_events SET convert_status = 'pending' WHERE id = ? AND convert_status = 'failed'",
                        (event_id,))
        self.wake()


def _size(n: int) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{n} B"

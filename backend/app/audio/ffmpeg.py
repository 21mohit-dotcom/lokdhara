"""Runs ffprobe and FFmpeg on uploaded files (docs/AUDIO_PROCESSING_PIPELINE.md §3.2, §3.3, §5).

Uploaded files are untrusted, so every call:

- passes an argument list, never a shell string, and never includes anything the client sent
  (paths are temporary files named by the worker);
- reads local files only (`-protocol_whitelist file`), so a crafted playlist cannot fetch URLs;
- forces the demuxer for the container the API recognised, so FFmpeg never guesses among its
  hundreds of input formats;
- has a time limit.
"""

import json
import subprocess
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

# Container recognised by app.audio_formats → FFmpeg demuxer that reads it.
DEMUXERS = {
    "webm": "matroska",
    "ogg": "ogg",
    "wav": "wav",
    "flac": "flac",
    "m4a": "mov",
    "aac": "aac",
    "mp3": "mp3",
}


class FfmpegTimeout(Exception):
    """The tool ran longer than allowed. Raised for probe and decode alike."""


@dataclass(frozen=True)
class Stream:
    codec_type: str
    codec_name: str | None
    sample_rate_hz: int | None
    channels: int | None
    bits_per_sample: int | None
    attached_pic: bool  # cover art in MP3/M4A, not a real video


@dataclass(frozen=True)
class Probe:
    format_name: str
    streams: tuple[Stream, ...]


@dataclass(frozen=True)
class Decoded:
    errors: bool  # FFmpeg reported a decoding error: the file is damaged or truncated
    duration_ms: int  # of what could be decoded, at most the decode limit


def _input(container: str, path: Path) -> list[str]:
    return ["-protocol_whitelist", "file", "-f", DEMUXERS[container], "-i", str(path)]


def _run(args: list[str], timeout: float) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(  # noqa: S603 - fixed program, argument list, no shell
            args, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise FfmpegTimeout(args[0]) from exc


def _int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def probe(path: Path, container: str, *, timeout: float) -> Probe | None:
    """What the file says about itself, or None when ffprobe cannot read it at all."""
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            *_input(container, path),
            "-show_entries",
            "format=format_name:stream=codec_type,codec_name,sample_rate,channels,"
            "bits_per_sample,bits_per_raw_sample:stream_disposition=attached_pic",
            "-of",
            "json",
        ],
        timeout,
    )
    if result.returncode != 0:
        return None
    try:
        report = json.loads(result.stdout)
    except ValueError:
        return None
    streams = tuple(
        Stream(
            codec_type=str(s.get("codec_type", "")),
            codec_name=s.get("codec_name"),
            sample_rate_hz=_int(s.get("sample_rate")),
            channels=_int(s.get("channels")),
            # PCM reports bits_per_sample, FLAC bits_per_raw_sample; lossy codecs neither.
            bits_per_sample=_int(s.get("bits_per_raw_sample")) or _int(s.get("bits_per_sample")),
            attached_pic=bool(s.get("disposition", {}).get("attached_pic")),
        )
        for s in report.get("streams", [])
    )
    return Probe(format_name=str(report.get("format", {}).get("format_name", "")), streams=streams)


def decode(path: Path, container: str, *, timeout: float, max_seconds: float) -> Decoded:
    """Decodes the first audio stream completely, discarding the output.

    This is the real integrity check: anything FFmpeg reports at error level means damage.
    It also measures the duration, because browser WebM files carry none in their header.
    Decoding stops just after `max_seconds`, so a very long file costs no more than that.
    """
    result = _run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-v",
            "error",
            "-xerror",
            "-t",
            f"{max_seconds + 1:g}",
            *_input(container, path),
            "-map",
            "0:a:0",
            "-f",
            "null",
            "-progress",
            "pipe:1",
            "-",
        ],
        timeout,
    )
    duration_us = 0
    for line in result.stdout.decode("ascii", "replace").splitlines():
        key, _, value = line.partition("=")
        if key == "out_time_us" and value.strip().lstrip("-").isdigit():
            duration_us = max(int(value), 0)
    return Decoded(
        errors=result.returncode != 0 or bool(result.stderr.strip()),
        duration_ms=duration_us // 1000,
    )


@cache
def versions() -> dict[str, str]:
    """First line of `-version` for each tool, recorded with every processing run."""
    found = {}
    for tool in ("ffmpeg", "ffprobe"):
        output = _run([tool, "-version"], timeout=30).stdout.decode("utf-8", "replace")
        found[tool] = output.splitlines()[0] if output else "unknown"
    return found

"""Synthetic audio made with FFmpeg at test time. Audio files are never committed."""

import shutil
import subprocess
from pathlib import Path

import pytest

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
requires_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="FFmpeg is not installed (CI installs it)",
)

# Container → FFmpeg output arguments.
ENCODINGS = {
    "webm": ["-c:a", "libopus", "-f", "webm"],
    "ogg": ["-c:a", "libopus", "-f", "ogg"],
    "wav": ["-c:a", "pcm_s16le", "-f", "wav"],
    "flac": ["-c:a", "flac", "-f", "flac"],
    "m4a": ["-c:a", "aac", "-f", "ipod"],
    "aac": ["-c:a", "aac", "-f", "adts"],
    "mp3": ["-c:a", "libmp3lame", "-f", "mp3"],
}


def make_audio(
    path: Path,
    container: str = "webm",
    *,
    seconds: float = 2,
    rate: int = 48000,
    channels: int = 1,
    source: str | None = None,
    extra: tuple[str, ...] = (),
) -> bytes:
    """Encodes a tone (or another lavfi `source`) and returns the file's bytes."""
    lavfi = source or f"sine=frequency=220:sample_rate={rate}:duration={seconds}"
    subprocess.run(  # noqa: S603 - test helper, fixed program
        [
            FFMPEG,
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            lavfi,
            *extra,
            "-ac",
            str(channels),
            "-ar",
            str(rate),
            *ENCODINGS[container],
            str(path),
        ],
        check=True,
        timeout=60,
    )
    return path.read_bytes()

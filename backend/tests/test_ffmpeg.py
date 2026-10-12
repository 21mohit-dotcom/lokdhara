"""Running ffprobe and FFmpeg on uploaded files. All audio is generated here."""

import subprocess
from pathlib import Path

import pytest

from app.audio import ffmpeg
from tests.audio_fixtures import ENCODINGS, FFMPEG, make_audio, requires_ffmpeg

pytestmark = requires_ffmpeg

CODECS = {
    "webm": "opus",
    "ogg": "opus",
    "wav": "pcm_s16le",
    "flac": "flac",
    "m4a": "aac",
    "aac": "aac",
    "mp3": "mp3",
}


@pytest.mark.parametrize("container", ENCODINGS)
def test_reads_every_accepted_container(tmp_path: Path, container: str) -> None:
    path = tmp_path / "input"
    make_audio(path, container, seconds=3, rate=48000 if container in ("webm", "ogg") else 44100)

    found = ffmpeg.probe(path, container, timeout=30)
    assert found is not None
    [stream] = found.streams
    assert stream.codec_type == "audio"
    assert stream.codec_name == CODECS[container]
    assert stream.channels == 1

    decoded = ffmpeg.decode(path, container, timeout=30, max_seconds=60)
    assert not decoded.errors
    assert 2900 <= decoded.duration_ms <= 3100


def test_reports_bit_depth_of_lossless_files(tmp_path: Path) -> None:
    path = tmp_path / "input"
    make_audio(path, "flac", extra=("-sample_fmt", "s32"))
    found = ffmpeg.probe(path, "flac", timeout=30)
    assert found is not None
    assert found.streams[0].bits_per_sample == 24  # FLAC stores s32 input as 24-bit


@pytest.mark.parametrize("container", ["webm", "wav", "flac", "m4a", "aac"])
def test_truncated_files_are_damaged(tmp_path: Path, container: str) -> None:
    whole = make_audio(tmp_path / "whole", container, seconds=5)
    path = tmp_path / "input"
    path.write_bytes(whole[: len(whole) * 6 // 10])

    found = ffmpeg.probe(path, container, timeout=30)
    decoded = ffmpeg.decode(path, container, timeout=30, max_seconds=60)
    assert found is None or decoded.errors


def test_text_dressed_as_wav_is_not_readable(tmp_path: Path) -> None:
    path = tmp_path / "input"
    path.write_bytes(b"RIFF\x24\x08\x00\x00WAVE" + b"this is not audio " * 50)
    found = ffmpeg.probe(path, "wav", timeout=30)
    assert (
        found is None
        or not found.streams
        or ffmpeg.decode(path, "wav", timeout=30, max_seconds=60).errors
    )


def test_the_recognised_container_decides_the_demuxer(tmp_path: Path) -> None:
    path = tmp_path / "input"
    make_audio(path, "wav")
    # Told it is FLAC, FFmpeg reads it as FLAC (and finds nothing usable) instead of guessing WAV.
    found = ffmpeg.probe(path, "flac", timeout=30)
    assert found is None or found.format_name == "flac"
    assert ffmpeg.decode(path, "flac", timeout=30, max_seconds=60).errors


def test_reports_video_streams(tmp_path: Path) -> None:
    path = tmp_path / "input"
    subprocess.run(  # noqa: S603
        [
            FFMPEG, "-nostdin", "-v", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=64x64",
            "-f", "lavfi", "-i", "sine=duration=1",
            "-c:v", "mpeg4", "-c:a", "aac", "-f", "mp4", str(path),
        ],
        check=True,
        timeout=60,
    )  # fmt: skip
    found = ffmpeg.probe(path, "m4a", timeout=30)
    assert found is not None
    video = [s for s in found.streams if s.codec_type == "video"]
    assert video and not video[0].attached_pic


def test_decoding_stops_after_the_limit(tmp_path: Path) -> None:
    path = tmp_path / "input"
    make_audio(path, "wav", seconds=20, rate=8000)
    decoded = ffmpeg.decode(path, "wav", timeout=30, max_seconds=5)
    assert not decoded.errors
    assert 5000 < decoded.duration_ms <= 6100


def test_time_limit(tmp_path: Path) -> None:
    path = tmp_path / "input"
    make_audio(path, "flac", seconds=60)
    with pytest.raises(ffmpeg.FfmpegTimeout):
        ffmpeg.decode(path, "flac", timeout=0.001, max_seconds=600)


def test_versions_are_recorded() -> None:
    found = ffmpeg.versions()
    assert found["ffmpeg"].startswith("ffmpeg version")
    assert found["ffprobe"].startswith("ffprobe version")

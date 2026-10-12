"""The rules that accept or reject a recording, on made-up probe results (no audio needed)."""

import dataclasses

import pytest

from app.audio.ffmpeg import Decoded, Probe, Stream
from app.audio.validation import AudioInfo, Limits, Rejection, check_decode, check_probe

LIMITS = Limits(max_seconds=1800, max_channels=2, min_sample_rate_hz=8000, max_sample_rate_hz=96000)
OPUS = Stream("audio", "opus", 48000, 1, None, attached_pic=False)


def probe(*streams: Stream) -> Probe:
    return Probe("matroska,webm", streams)


def test_accepts_a_browser_recording() -> None:
    assert check_probe(probe(OPUS), LIMITS) == AudioInfo("opus", 48000, 1, None, is_lossy=True)


def test_keeps_the_bit_depth_of_lossless_audio() -> None:
    wav = Stream("audio", "pcm_s24le", 96000, 2, 24, attached_pic=False)
    assert check_probe(probe(wav), LIMITS) == AudioInfo("pcm_s24le", 96000, 2, 24, is_lossy=False)


def test_ignores_bit_depth_reported_for_lossy_audio() -> None:
    aac = dataclasses.replace(OPUS, codec_name="aac", bits_per_sample=16)
    info = check_probe(probe(aac), LIMITS)
    assert isinstance(info, AudioInfo)
    assert info.bit_depth is None


def test_cover_art_is_not_a_video() -> None:
    art = Stream("video", "mjpeg", None, None, None, attached_pic=True)
    assert isinstance(check_probe(probe(OPUS, art), LIMITS), AudioInfo)


@pytest.mark.parametrize(
    ("streams", "reason"),
    [
        ((), "no_audio_stream"),
        ((OPUS, OPUS), "several_audio_streams"),
        ((OPUS, Stream("video", "h264", None, None, None, attached_pic=False)), "video_stream"),
        ((dataclasses.replace(OPUS, codec_name="amr_nb"),), "codec_not_accepted"),
        ((dataclasses.replace(OPUS, codec_name="pcm_alaw"),), "codec_not_accepted"),
        ((dataclasses.replace(OPUS, channels=None),), "unreadable"),
    ],
)
def test_rejects_unsupported_files(streams: tuple[Stream, ...], reason: str) -> None:
    assert check_probe(probe(*streams), LIMITS) == Rejection("unsupported_format", reason)


def test_rejects_what_ffprobe_cannot_read() -> None:
    assert check_probe(None, LIMITS) == Rejection("unsupported_format", "unreadable")


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"channels": 3}, "too_many_channels"),
        ({"sample_rate_hz": 4000}, "sample_rate"),
        ({"sample_rate_hz": 192000}, "sample_rate"),
    ],
)
def test_rejects_values_outside_the_limits(changes: dict[str, int], reason: str) -> None:
    stream = dataclasses.replace(OPUS, **changes)  # type: ignore[arg-type]
    assert check_probe(probe(stream), LIMITS) == Rejection("out_of_range", reason)


@pytest.mark.parametrize("rate", [8000, 96000])
def test_limits_are_inclusive(rate: int) -> None:
    assert isinstance(
        check_probe(probe(dataclasses.replace(OPUS, sample_rate_hz=rate)), LIMITS), AudioInfo
    )


@pytest.mark.parametrize(
    ("decoded", "expected"),
    [
        (Decoded(errors=False, duration_ms=500), None),  # short recordings are flagged later
        (Decoded(errors=False, duration_ms=1_800_000), None),
        (Decoded(errors=False, duration_ms=1_800_001), Rejection("out_of_range", "too_long")),
        (Decoded(errors=True, duration_ms=3000), Rejection("corrupt_audio", "decode_errors")),
        (Decoded(errors=False, duration_ms=0), Rejection("corrupt_audio", "no_audio_decoded")),
    ],
)
def test_decode_result(decoded: Decoded, expected: Rejection | None) -> None:
    assert check_decode(decoded, LIMITS) == expected

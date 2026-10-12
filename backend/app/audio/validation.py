"""Decides whether a probed and decoded file is an acceptable recording
(docs/AUDIO_PROCESSING_PIPELINE.md §1, §2, §3.2, §3.3). Pure functions, no I/O.

A rejection carries a stable `code` the contributor's app can explain and a `reason` for admins.
Recordings under a second are not rejected here: `audio.analyze` flags them as `too_short`
for the reviewer, because flags never reject on their own in the MVP.
"""

from dataclasses import dataclass

from app.audio.ffmpeg import Decoded, Probe

LOSSY_CODECS = frozenset({"opus", "vorbis", "aac", "mp3"})
LOSSLESS_CODECS = frozenset({"flac", "pcm_u8", "pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm_f32le"})


@dataclass(frozen=True)
class Limits:
    max_seconds: float
    max_channels: int
    min_sample_rate_hz: int
    max_sample_rate_hz: int


@dataclass(frozen=True)
class Rejection:
    code: str  # unsupported_format | out_of_range | corrupt_audio
    reason: str


@dataclass(frozen=True)
class AudioInfo:
    codec: str
    sample_rate_hz: int
    channels: int
    bit_depth: int | None  # None for lossy codecs, where it has no meaning
    is_lossy: bool


def check_probe(probe: Probe | None, limits: Limits) -> AudioInfo | Rejection:
    if probe is None:
        return Rejection("unsupported_format", "unreadable")
    if any(s.codec_type == "video" and not s.attached_pic for s in probe.streams):
        return Rejection("unsupported_format", "video_stream")  # cover art is fine
    audio = [s for s in probe.streams if s.codec_type == "audio"]
    if not audio:
        return Rejection("unsupported_format", "no_audio_stream")
    if len(audio) > 1:
        return Rejection("unsupported_format", "several_audio_streams")
    [stream] = audio
    codec = stream.codec_name or ""
    if codec not in LOSSY_CODECS | LOSSLESS_CODECS:
        return Rejection("unsupported_format", "codec_not_accepted")
    if stream.channels is None or stream.sample_rate_hz is None:
        return Rejection("unsupported_format", "unreadable")
    if stream.channels > limits.max_channels:
        return Rejection("out_of_range", "too_many_channels")
    if not limits.min_sample_rate_hz <= stream.sample_rate_hz <= limits.max_sample_rate_hz:
        return Rejection("out_of_range", "sample_rate")
    lossy = codec in LOSSY_CODECS
    return AudioInfo(
        codec=codec,
        sample_rate_hz=stream.sample_rate_hz,
        channels=stream.channels,
        bit_depth=None if lossy else stream.bits_per_sample,
        is_lossy=lossy,
    )


def check_decode(decoded: Decoded, limits: Limits) -> Rejection | None:
    if decoded.errors:
        return Rejection("corrupt_audio", "decode_errors")
    if decoded.duration_ms == 0:
        return Rejection("corrupt_audio", "no_audio_decoded")
    if decoded.duration_ms > limits.max_seconds * 1000:
        return Rejection("out_of_range", "too_long")
    return None

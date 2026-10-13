"""Derived copies of an original recording (docs/AUDIO_PROCESSING_PIPELINE.md §3.6).

Each kind is defined by the exact FFmpeg output arguments that make it. Those arguments, and a
format version, are the rendition's `params`; their hash keeps re-runs from duplicating a
rendition and lets a changed recipe produce a new one beside the old. Pure, apart from reading
the decoded samples for the waveform.
"""

import hashlib
import json
import sys
from array import array
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from app.object_store import new_key

# Never copy the original's tags (titles, artists, comments may contain names) or chapters,
# and leave out encoder version strings, so the same input gives the same bytes.
_CLEAN = ("-map_metadata", "-1", "-map_chapters", "-1", "-fflags", "+bitexact")


@dataclass(frozen=True)
class Kind:
    name: str
    extension: str
    content_type: str
    output_args: tuple[str, ...]

    @property
    def params(self) -> dict[str, Any]:
        return {"format_version": 1, "ffmpeg_output_args": list(self.output_args)}

    @property
    def params_sha256(self) -> str:
        canonical = json.dumps(self.params, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()


# Lossless 16 kHz mono: the working copy for research tools, and the source of the waveform.
ANALYSIS = Kind(
    "analysis_flac_16k_mono",
    "flac",
    "audio/flac",
    (*_CLEAN, "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", "-c:a", "flac", "-f", "flac"),
)
# Small files for listening on slow connections; AAC for browsers without Opus (Q-T2).
PLAYBACK_OPUS = Kind(
    "playback_opus",
    "webm",
    "audio/webm",
    (*_CLEAN, "-ac", "1", "-c:a", "libopus", "-b:a", "24k", "-application", "voip", "-f", "webm"),
)
PLAYBACK_AAC = Kind(
    "playback_aac",
    "m4a",
    "audio/mp4",
    (*_CLEAN, "-ac", "1", "-c:a", "aac", "-b:a", "48k", "-movflags", "+faststart", "-f", "ipod"),
)
AUDIO_KINDS = (ANALYSIS, PLAYBACK_OPUS, PLAYBACK_AAC)

# The waveform is computed from 16 kHz mono samples, decoded to raw 16-bit integers.
PCM_ARGS = (*_CLEAN, "-ac", "1", "-ar", "16000", "-f", "s16le", "-c:a", "pcm_s16le")
PEAKS_PER_SECOND = 20
_SAMPLES_PER_PEAK = 16000 // PEAKS_PER_SECOND
WAVEFORM = Kind("waveform_peaks", "json", "application/json", PCM_ARGS)


def derived_key(original_key: str, kind: Kind) -> str:
    """Next to the original's key, e.g. 2026/10/<recording id>/playback_opus-<hash>.webm."""
    folder = PurePosixPath(original_key).parent
    return new_key(
        *folder.parts, f"{kind.name}-{kind.params_sha256[:16]}", suffix=f".{kind.extension}"
    )


def waveform(pcm: Path) -> bytes:
    """Peak level per 1/20 s as whole percentages of full scale, as compact JSON."""
    peaks = []
    with pcm.open("rb") as file:
        while chunk := file.read(_SAMPLES_PER_PEAK * 2):
            samples = array("h")
            samples.frombytes(chunk[: len(chunk) // 2 * 2])
            if sys.byteorder == "big":
                samples.byteswap()
            if samples:
                loudest = max(max(samples), -min(samples))
                peaks.append(min(100, round(loudest * 100 / 32768)))
    document = {"version": 1, "peaks_per_second": PEAKS_PER_SECOND, "peaks": peaks}
    return json.dumps(document, separators=(",", ":")).encode()

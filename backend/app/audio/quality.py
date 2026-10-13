"""Quality measurements and flags for reviewers (docs/AUDIO_PROCESSING_PIPELINE.md §3.5).

One FFmpeg pass runs `silencedetect`, `ebur128`, and `astats`; this module turns its log into
numbers and the numbers into flags. Flags are hints for the reviewer and never reject a
recording. The thresholds are first guesses, to be tuned on real recordings in the pilot.
"""

import math
import re
from dataclasses import asdict, dataclass

SILENCE_NOISE_DB = -50  # quieter than this counts as silence …
SILENCE_MIN_SECONDS = 0.5  # … when it lasts at least this long
SILENT_RATIO = 0.95  # `silent` when more of the recording than this is silence
VERY_QUIET_RMS_DBFS = -45.0  # `very_quiet` below this average level
CLIPPED_PEAK_DBFS = -0.1  # samples only count as clipped when the peak reaches this
CLIPPING_RATIO = 0.001  # `clipping` when more than 0.1 % of samples are clipped

ANALYSIS_FLAGS = frozenset({"silent", "too_short", "clipping", "very_quiet"})

FILTERS = ",".join(
    [
        f"silencedetect=noise={SILENCE_NOISE_DB}dB:d={SILENCE_MIN_SECONDS}",
        # Per-100 ms loudness lines go to the verbose level; only the summary is logged.
        "ebur128=peak=true:framelog=verbose",
        # Whole-number samples saturate at full scale, so clipping can be counted even in
        # lossy recordings, which decode to floating point and can exceed it.
        "aformat=sample_fmts=s16",
        "astats=metadata=0:measure_perchannel=none",
    ]
)

_ASTATS = re.compile(
    r"^\[Parsed_astats_\d+ @ [^\]]+\] (Peak level dB|RMS level dB|Peak count|Number of samples):"
    r" (\S+)$",
    re.MULTILINE,
)
_INTEGRATED = re.compile(r"^\s+I:\s+(\S+) LUFS$", re.MULTILINE)
_TRUE_PEAK = re.compile(r"^\s+Peak:\s+(\S+) dBFS$", re.MULTILINE)
_SILENCE = re.compile(r"\] silence_end: \S+ \| silence_duration: (\S+)$", re.MULTILINE)


@dataclass(frozen=True)
class Metrics:
    """Stored in `recordings.quality_metrics`. None stands for minus infinity (no signal)."""

    peak_dbfs: float | None
    rms_dbfs: float | None
    integrated_lufs: float | None
    true_peak_dbtp: float | None
    clipping_ratio: float  # an estimate: samples at full scale / all samples
    silence_ratio: float

    def as_json(self) -> dict[str, float | None]:
        return asdict(self)


def _number(text: str) -> float | None:
    value = float(text)
    return round(value, 2) if math.isfinite(value) else None


def _last(pattern: re.Pattern[str], log: str) -> str:
    found = pattern.findall(log)
    if not found:
        raise ValueError(f"analysis log has no match for {pattern.pattern[:30]!r}")
    return str(found[-1])


def parse(log: str, duration_ms: int) -> Metrics:
    """Reads the numbers out of FFmpeg's log. Raises ValueError if a summary is missing."""
    stats = {name: value for name, value in _ASTATS.findall(log)}
    if len(stats) < 4:
        raise ValueError("analysis log has no astats summary")
    peak = _number(stats["Peak level dB"])
    samples = float(stats["Number of samples"])
    clipped = float(stats["Peak count"]) if peak is not None and peak >= CLIPPED_PEAK_DBFS else 0
    silence = sum(float(seconds) for seconds in _SILENCE.findall(log))
    seconds = duration_ms / 1000
    return Metrics(
        peak_dbfs=peak,
        rms_dbfs=_number(stats["RMS level dB"]),
        integrated_lufs=_number(_last(_INTEGRATED, log)),
        true_peak_dbtp=_number(_last(_TRUE_PEAK, log)),
        clipping_ratio=round(min(clipped / samples, 1.0), 4) if samples else 0.0,
        silence_ratio=round(min(silence / seconds, 1.0), 4) if seconds else 1.0,
    )


def flags(metrics: Metrics, duration_ms: int, min_seconds: float) -> set[str]:
    found = set()
    if duration_ms < min_seconds * 1000:
        found.add("too_short")
    if metrics.silence_ratio > SILENT_RATIO:
        found.add("silent")
    if metrics.rms_dbfs is None or metrics.rms_dbfs < VERY_QUIET_RMS_DBFS:
        found.add("very_quiet")
    if metrics.clipping_ratio > CLIPPING_RATIO:
        found.add("clipping")
    return found

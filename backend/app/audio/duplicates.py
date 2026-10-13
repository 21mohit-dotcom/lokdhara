"""Fingerprints for finding the same recording uploaded twice (docs/AUDIO_PROCESSING_PIPELINE.md
§3.7).

The same file has the same `sha256_original`. The same sound in another container or encoding
(a WAV re-saved as FLAC, say) has the same decoded samples, so `sha256_pcm` hashes the 16 kHz
mono samples. Decoders may differ slightly between FFmpeg versions, so the FFmpeg version is
hashed in too: recordings fingerprinted by different versions never match, which can miss a
duplicate but never invents one. Near-duplicates (trimmed or re-recorded audio) are not
detected (Q-T5).
"""

import hashlib
from pathlib import Path

from app.audio.renditions import PCM_ARGS

__all__ = ["PCM_ARGS", "pcm_sha256"]

_CHUNK = 1024 * 1024


def pcm_sha256(pcm: Path, ffmpeg_version: str) -> str:
    """Hash of the decoded samples in `pcm` (made with PCM_ARGS) and the decoder's version."""
    digest = hashlib.sha256(ffmpeg_version.encode() + b"\n")
    with pcm.open("rb") as file:
        while chunk := file.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()

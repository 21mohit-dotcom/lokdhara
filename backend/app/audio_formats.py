"""Recognise audio containers from their first bytes (magic numbers).

This is a cheap first gate that rejects files which are obviously not audio. It proves nothing
about the content: full ffprobe and decode validation happens in the worker
(docs/AUDIO_PROCESSING_PIPELINE.md).
"""

SNIFF_BYTES = 16

CONTENT_TYPES = {
    "webm": "audio/webm",
    "ogg": "audio/ogg",
    "wav": "audio/wav",
    "flac": "audio/flac",
    "m4a": "audio/mp4",
    "aac": "audio/aac",
    "mp3": "audio/mpeg",
}


def sniff_audio_container(head: bytes) -> str | None:
    """Returns a file extension for a recognised audio container, otherwise None."""
    if head.startswith(b"\x1a\x45\xdf\xa3"):  # EBML: WebM / Matroska
        return "webm"
    if head.startswith(b"OggS"):
        return "ogg"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if head.startswith(b"fLaC"):
        return "flac"
    if head[4:8] == b"ftyp":  # MP4 family, e.g. iPhone and Android recorder .m4a
        return "m4a"
    if len(head) >= 2 and head[0] == 0xFF:
        if head[1] & 0xF6 == 0xF0:  # ADTS: 12 sync bits, layer 00 (raw AAC from recorder apps)
            return "aac"
        if head[1] & 0xE0 == 0xE0:  # MPEG audio frame sync
            return "mp3"
    if head.startswith(b"ID3"):
        return "mp3"
    return None

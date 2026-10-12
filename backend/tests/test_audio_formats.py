"""The cheap first gate on uploaded audio: recognise containers by their first bytes."""

import pytest

from app.audio_formats import CONTENT_TYPES, sniff_audio_container

# Synthetic headers only: the bytes each container starts with, padded to 16 bytes.
HEADERS = {
    "webm": b"\x1a\x45\xdf\xa3\x9f\x42\x86\x81",
    "ogg": b"OggS\x00\x02",
    "wav": b"RIFF\x24\x08\x00\x00WAVEfmt ",
    "flac": b"fLaC\x00\x00\x00\x22",
    "m4a": b"\x00\x00\x00\x20ftypM4A ",
    "aac": b"\xff\xf1\x50\x80",  # ADTS, as saved by Android recorder apps (Q-T1)
    "mp3": b"\xff\xfb\x90\x64",
}


@pytest.mark.parametrize(("expected", "head"), HEADERS.items())
def test_recognises_supported_containers(expected: str, head: bytes) -> None:
    assert sniff_audio_container(head.ljust(16, b"\x00")) == expected
    assert expected in CONTENT_TYPES


def test_id3_tagged_mp3() -> None:
    assert sniff_audio_container(b"ID3\x04\x00\x00\x00\x00\x00\x00") == "mp3"


@pytest.mark.parametrize(
    "head",
    [b"", b"%PDF-1.7", b"\x89PNG\r\n\x1a\n", b"PK\x03\x04", b"RIFF\x00\x00\x00\x00AVI ", b"\xff"],
)
def test_rejects_everything_else(head: bytes) -> None:
    assert sniff_audio_container(head) is None

import pytest

from app.image_formats import CONTENT_TYPES, sniff_image


@pytest.mark.parametrize(
    ("head", "expected"),
    [
        (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", "png"),
        (b"\xff\xd8\xff\xe0\x00\x10JFIF", "jpg"),
        (b"RIFF\x24\x00\x00\x00WEBPVP8 ", "webp"),
    ],
)
def test_recognises_supported_images(head: bytes, expected: str) -> None:
    assert sniff_image(head) == expected
    assert expected in CONTENT_TYPES


@pytest.mark.parametrize(
    "head", [b"<svg xmlns=", b"GIF89a", b"RIFF\x24\x00\x00\x00WAVEfmt ", b"%PDF-1.7", b""]
)
def test_refuses_everything_else(head: bytes) -> None:
    assert sniff_image(head) is None

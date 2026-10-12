"""Recognise prompt images from their first bytes. Only common, safe raster formats are taken;
SVG is refused because it can carry scripts."""

SNIFF_BYTES = 16

CONTENT_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "webp": "image/webp",
}


def sniff_image(head: bytes) -> str | None:
    """Returns a file extension for PNG, JPEG, or WebP, otherwise None."""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None

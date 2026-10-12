"""Derived forms of stored text (docs/TEXT_PROCESSING_PIPELINE.md §3)."""

import unicodedata


def to_nfc(text: str) -> str:
    """`content_nfc`: canonical composition (never NFKC) with LF line endings."""
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))

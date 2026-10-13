"""Derived forms of stored text (docs/TEXT_PROCESSING_PIPELINE.md §3)."""

import re
import unicodedata


def to_nfc(text: str) -> str:
    """`content_nfc`: canonical composition (never NFKC) with LF line endings."""
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


# Spaces, tabs, and no-break spaces; newlines are kept because line structure matters in songs.
SPACE_RUN = r"[ \t\u00a0]+"


def search_key(nfc: str) -> str:
    """The form compared by search and duplicate checks (§4): runs of spaces become one space
    and the ends are trimmed. Never stored as a revision; `text.derive` computes the same in SQL.
    """
    return re.sub(SPACE_RUN, " ", nfc).strip(" \n")

"""Safety checks before text is stored (docs/TEXT_PROCESSING_PIPELINE.md §2).

Text that fails is rejected with a stable code, never repaired: the stored original must be
exactly what the person typed (ADR-010).
"""

import unicodedata

# Initial limits by entry type; transcriptions and translations use the long-text limit.
MAX_LENGTH = {
    "word": 200,
    "phrase": 200,
    "sentence": 1_000,
    "paragraph": 5_000,
    "long_text": 50_000,
}
LONGEST = max(MAX_LENGTH.values())

_ALLOWED_CONTROLS = frozenset("\t\n\r")
# Explicit embeddings, overrides, and isolates: they can make a reviewer see different text.
_BIDI_CONTROLS = frozenset("‪‫‬‭‮⁦⁧⁨⁩")
# Control (C0/C1), surrogate, private use, and unassigned (which includes noncharacters).
_REJECTED_CATEGORIES = frozenset({"Cc", "Cs", "Co", "Cn"})


class TextRejected(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def check(text: str, entry_type: str | None = None) -> str:
    """Returns `text` unchanged if it is safe to store, otherwise raises TextRejected.

    ZWJ and ZWNJ are format characters (Cf), not controls, so they pass: they change how
    Devanagari and other Indic scripts render.
    """
    if not text.strip():
        raise TextRejected("text_empty")
    if len(text) > MAX_LENGTH.get(entry_type or "long_text", LONGEST):
        raise TextRejected("text_too_long")
    for char in text:
        if char in _ALLOWED_CONTROLS:
            continue
        if char in _BIDI_CONTROLS or unicodedata.category(char) in _REJECTED_CATEGORIES:
            raise TextRejected("disallowed_character")
    return text

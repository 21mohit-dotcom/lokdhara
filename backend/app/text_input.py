"""Validation for free text typed by people (names, notes, references).

Control characters and bidirectional overrides are rejected, not stripped: they can hide or
reorder what a reviewer sees (docs/PRIVACY_AND_SECURITY.md). Text is otherwise kept as typed.
"""

import unicodedata
from typing import Annotated

from pydantic import AfterValidator

# Explicit embeddings, overrides, and isolates (U+202A-U+202E, U+2066-U+2069).
_BIDI_CONTROLS = frozenset("‪‫‬‭‮⁦⁧⁨⁩")
_MULTILINE_ALLOWED = frozenset("\n\t")


def _check(value: str, allowed: frozenset[str]) -> str:
    for char in value:
        if char in _BIDI_CONTROLS:
            raise ValueError("text contains a bidirectional control character")
        if unicodedata.category(char) == "Cc" and char not in allowed:
            raise ValueError("text contains a control character")
    stripped = value.strip()
    if not stripped:
        raise ValueError("text is empty")
    return stripped


def single_line(value: str) -> str:
    return _check(value, frozenset())


def multi_line(value: str) -> str:
    return _check(value.replace("\r\n", "\n"), _MULTILINE_ALLOWED)


SingleLine = Annotated[str, AfterValidator(single_line)]
MultiLine = Annotated[str, AfterValidator(multi_line)]

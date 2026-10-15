"""Differences between two versions of a text, for showing what a revision changed.

Text is compared by user-perceived characters (grapheme clusters), so a Devanagari consonant
and its vowel sign stay together instead of a diff splitting them. Nothing here changes text.
"""

from difflib import SequenceMatcher
from typing import Literal

import regex

Op = Literal["equal", "delete", "insert"]

_GRAPHEME = regex.compile(r"\X")


def graphemes(text: str) -> list[str]:
    return _GRAPHEME.findall(text)


def diff(old: str, new: str) -> list[tuple[Op, str]]:
    """Parts in reading order; joining the `equal` and `delete` parts gives `old`, the
    `equal` and `insert` parts give `new`. A replacement is a delete followed by an insert."""
    a, b = graphemes(old), graphemes(new)
    parts: list[tuple[Op, str]] = []

    def add(op: Op, chunk: list[str]) -> None:
        if not chunk:
            return
        text = "".join(chunk)
        if parts and parts[-1][0] == op:
            parts[-1] = (op, parts[-1][1] + text)
        else:
            parts.append((op, text))

    matcher = SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            add("equal", a[i1:i2])
        else:
            add("delete", a[i1:i2])
            add("insert", b[j1:j2])
    return parts

"""Transcription markup, provisional until linguists decide (Q-X3,
docs/TEXT_PROCESSING_PIPELINE.md §8).

Provisional markup: `[?word]` unsure, `[inaudible]`, `[overlap]`, `[hi: …]` code-switch,
`[laugh]`, `[cough]`, `[noise]`.
"""

import re

_UNCERTAIN = re.compile(r"\[\?[^\[\]\n]*\]|\[inaudible\]")
# `[inaudible]`, `[noise]`, … are tags; `[?word]` and `[hi: words]` wrap words that were said.
_TAG = re.compile(r"\[[a-z]+\]")
_WRAPPED = re.compile(r"\[(?:\?|[a-z]{2,3}:)([^\[\]\n]*)\]")


def has_uncertainty(text: str) -> bool:
    """True when the text marks something unsure or unheard; such a revision cannot be
    verified until a reviewer resolves or explicitly accepts it."""
    return _UNCERTAIN.search(text) is not None


def without_tags(text: str) -> str:
    """The words of a transcription without the markup around them, for script detection."""
    return _WRAPPED.sub(r"\1", _TAG.sub(" ", text))

"""Transcription markup, provisional until linguists decide (Q-X3,
docs/TEXT_PROCESSING_PIPELINE.md §8).

Provisional markup: `[?word]` unsure, `[inaudible]`, `[overlap]`, `[hi: …]` code-switch,
`[laugh]`, `[cough]`, `[noise]`.
"""

import re

_UNCERTAIN = re.compile(r"\[\?[^\[\]\n]*\]|\[inaudible\]")


def has_uncertainty(text: str) -> bool:
    """True when the text marks something unsure or unheard; such a revision cannot be
    verified until a reviewer resolves or explicitly accepts it."""
    return _UNCERTAIN.search(text) is not None

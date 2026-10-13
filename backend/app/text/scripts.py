"""Which writing systems a text uses (docs/TEXT_PROCESSING_PIPELINE.md §5).

Detection only describes the text: a difference from the script the contributor chose is shown
as a warning and never corrected. Digits, punctuation, spaces, and combining marks shared by
many scripts (Unicode scripts Common and Inherited) are not counted.
"""

from collections import Counter

import regex

from app.text import markup

# ISO 15924 code → Unicode script name, for the scripts Mundari and its translations use.
KNOWN = {
    "Deva": "Devanagari",
    "Latn": "Latin",
    "Nagm": "Nag_Mundari",
    "Beng": "Bengali",
    "Orya": "Oriya",
}
# Letters in any other script are counted together under Zyyy (undetermined).
OTHER = "Zyyy"

_SCRIPT = regex.compile(
    "|".join(f"(?P<{code}>\\p{{Script={name}}})" for code, name in KNOWN.items())
    + f"|(?P<{OTHER}>[^\\p{{Script=Common}}\\p{{Script=Inherited}}])"
)


def detect(text: str) -> list[str]:
    """Scripts present in `text`, the most used first. Markup tags such as `[inaudible]` are
    left out, so an English tag does not make a Devanagari transcription look mixed."""
    counts = Counter(
        match.lastgroup or OTHER for match in _SCRIPT.finditer(markup.without_tags(text))
    )
    return [code for code, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def mismatch(declared: str, detected: list[str]) -> bool:
    """True when the chosen script does not appear at all. Mixed text, such as Mundari in
    Devanagari with an English loanword, is normal and not a mismatch."""
    return declared != OTHER and bool(detected) and declared not in detected

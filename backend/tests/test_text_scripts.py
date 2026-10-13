"""Script detection (docs/TEXT_PROCESSING_PIPELINE.md §5).

Sample strings are synthetic or common words, never collected community text.
"""

import pytest

from app.text import markup, scripts

NAG_MUNDARI = "\U0001e4d0\U0001e4d1\U0001e4d2"


@pytest.mark.parametrize(
    ("text", "found"),
    [
        ("जोहार", ["Deva"]),
        ("Johar", ["Latn"]),
        ("é", ["Latn"]),  # e + combining acute: the mark belongs to no script of its own
        (NAG_MUNDARI, ["Nagm"]),
        ("জোহার", ["Beng"]),
        ("ଜୋହାର", ["Orya"]),
        ("क्‍ष क्‌ष", ["Deva"]),  # ZWJ and ZWNJ are not counted
        ("जोहार school जोहार", ["Deva", "Latn"]),  # the most used comes first
        ("Привет", ["Zyyy"]),  # any script not on the list
        ("123 ... !?", []),
        ("१२३", ["Deva"]),  # Devanagari digits belong to Devanagari
    ],
)
def test_detect(text: str, found: list[str]) -> None:
    assert scripts.detect(text) == found


def test_markup_tags_are_not_counted_but_the_words_inside_are() -> None:
    text = "जोहार [inaudible] [?दिसुम] [noise] [hi: नमस्ते]"
    assert markup.without_tags(text).split() == ["जोहार", "दिसुम", "नमस्ते"]
    assert scripts.detect(text) == ["Deva"]
    assert scripts.detect("Johar [hi: नमस्ते जी]") == ["Deva", "Latn"]


@pytest.mark.parametrize(
    ("declared", "detected", "expected"),
    [
        ("Deva", ["Deva"], False),
        ("Deva", ["Deva", "Latn"], False),  # a loanword in Latin script is normal
        ("Deva", ["Latn"], True),
        ("Nagm", ["Deva"], True),
        ("Latn", [], False),  # only digits and punctuation: nothing to compare
        ("Zyyy", ["Latn"], False),  # the contributor said the script is mixed or unknown
    ],
)
def test_mismatch(declared: str, detected: list[str], expected: bool) -> None:
    assert scripts.mismatch(declared, detected) is expected


def test_every_detected_code_is_allowed_by_the_database() -> None:
    allowed = {"Deva", "Latn", "Nagm", "Beng", "Orya", "Zyyy"}  # ck_text_revisions_detected_scripts
    assert {*scripts.KNOWN, scripts.OTHER} == allowed

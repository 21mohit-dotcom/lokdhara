"""Text safety, NFC, and markup rules (docs/TEXT_PROCESSING_PIPELINE.md §2, §3, §8).

Sample strings are synthetic or common words, never collected community text.
"""

import sys
import unicodedata

import pytest

from app.text import markup, normalize, safety

# Devanagari, Latin with a combining mark, Nag Mundari letters, and mixed script.
SAMPLES = [
    "जोहार",
    "Johar",
    "é",  # e + combining acute
    "\U0001e4d0\U0001e4d1\U0001e4d2",
    "क्‍ष",  # ZWJ
    "क्‌ष",  # ZWNJ
    "जोहार Johar!\nदूसरी पंक्ति\r\n\tइंडेंट",
]


@pytest.mark.parametrize("text", SAMPLES)
def test_safe_text_is_returned_unchanged(text: str) -> None:
    assert safety.check(text) is text


def test_every_control_character_except_tab_and_newlines_is_rejected() -> None:
    controls = [chr(c) for c in range(sys.maxunicode + 1) if unicodedata.category(chr(c)) == "Cc"]
    assert len(controls) == 65
    for char in controls:
        text = f"a{char}b"
        if char in "\t\n\r":
            assert safety.check(text) == text
        else:
            with pytest.raises(safety.TextRejected, match="disallowed_character"):
                safety.check(text)


@pytest.mark.parametrize(
    "char",
    [
        *"‪‫‬‭‮⁦⁧⁨⁩",  # bidi controls
        "",  # private use
        "\U000f0000",  # supplementary private use
        "﷐",  # noncharacter
        "￿",  # noncharacter
        "\U000e0080",  # unassigned
        "\ud800",  # lone surrogate (only reachable through escaped JSON)
    ],
)
def test_characters_that_hide_or_garble_text_are_rejected(char: str) -> None:
    with pytest.raises(safety.TextRejected, match="disallowed_character"):
        safety.check(f"जोहार{char}")


@pytest.mark.parametrize("text", ["", "   ", "\n\t\r\n"])
def test_empty_text_is_rejected(text: str) -> None:
    with pytest.raises(safety.TextRejected, match="text_empty"):
        safety.check(text)


@pytest.mark.parametrize(
    ("entry_type", "limit"),
    [("word", 200), ("phrase", 200), ("sentence", 1_000), ("paragraph", 5_000), (None, 50_000)],
)
def test_length_limits_follow_the_entry_type(entry_type: str | None, limit: int) -> None:
    assert safety.check("क" * limit, entry_type)
    with pytest.raises(safety.TextRejected, match="text_too_long"):
        safety.check("क" * (limit + 1), entry_type)


def test_nfc_composes_and_keeps_joiners() -> None:
    decomposed = "é क़ क्‍ष"
    nfc = normalize.to_nfc(decomposed)
    assert nfc == unicodedata.normalize("NFC", decomposed)
    assert "é" in nfc and "‍" in nfc
    assert normalize.to_nfc(nfc) == nfc


def test_nfc_never_applies_compatibility_mappings() -> None:
    assert normalize.to_nfc("ﬁ x²") == "ﬁ x²"


def test_nfc_uses_lf_line_endings() -> None:
    assert normalize.to_nfc("एक\r\nदो\rतीन") == "एक\nदो\nतीन"


@pytest.mark.parametrize(
    ("text", "uncertain"),
    [
        ("वह [?घर] गया", True),
        ("[inaudible] जोहार", True),
        ("जोहार [overlap] [laugh] [hi: नमस्ते]", False),
        ("a [?] b", True),
        ("[? not closed", False),
        ("plain text", False),
    ],
)
def test_uncertainty_markup(text: str, uncertain: bool) -> None:
    assert markup.has_uncertainty(text) is uncertain

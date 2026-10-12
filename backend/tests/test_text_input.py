import pytest

from app.text_input import multi_line, single_line


def test_text_is_kept_as_typed_apart_from_surrounding_spaces() -> None:
    assert single_line("  होरो  ") == "होरो"
    assert multi_line("line one\r\nline two\t") == "line one\nline two"


@pytest.mark.parametrize("value", ["name‮evil", "a⁦b", "tab\tinside", "new\nline", "bell\x07"])
def test_single_line_rejects_hidden_controls(value: str) -> None:
    with pytest.raises(ValueError, match="character"):
        single_line(value)


def test_multi_line_allows_line_breaks_but_not_direction_overrides() -> None:
    assert multi_line("one\ntwo") == "one\ntwo"
    with pytest.raises(ValueError, match="bidirectional"):
        multi_line("one\n‫two")


def test_blank_text_is_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        single_line("   ")

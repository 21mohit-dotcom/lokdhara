import pytest
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from app.forms import parse_json_field


class Answers(BaseModel):
    agreed: bool
    note: str | None = None


def test_parses_the_json_part() -> None:
    assert parse_json_field(Answers, '{"agreed": true}', "answers") == Answers(agreed=True)


@pytest.mark.parametrize("raw", ['{"note": "x"}', "not json", '{"agreed": "maybe"}'])
def test_errors_point_at_the_form_field(raw: str) -> None:
    with pytest.raises(RequestValidationError) as caught:
        parse_json_field(Answers, raw, "answers")
    assert all(error["loc"][:2] == ("body", "answers") for error in caught.value.errors())

"""Multipart requests that carry a JSON document next to uploaded files.

Endpoints that take files receive the structured part as one JSON form field. It is validated
with the same Pydantic model and reported like any other request validation error.
"""

from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError


def parse_json_field[M: BaseModel](model: type[M], raw: str, field: str) -> M:
    try:
        return model.model_validate_json(raw)
    except ValidationError as exc:
        raise RequestValidationError(
            [{**error, "loc": ("body", field, *error["loc"])} for error in exc.errors()]
        ) from exc

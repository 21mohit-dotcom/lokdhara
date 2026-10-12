"""Language and script identifiers shared by speakers, prompts, submissions, and text."""

from typing import Annotated, Literal

from pydantic import StringConstraints

# BCP 47 language tag, e.g. "unr", "hi", "unr-Deva".
LanguageTag = Annotated[
    str, StringConstraints(pattern=r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$", max_length=35)
]
# ISO 15924 script codes (docs/TEXT_PROCESSING_PIPELINE.md); Zyyy when no script dominates.
Script = Literal["Deva", "Latn", "Nagm", "Beng", "Orya", "Zyyy"]

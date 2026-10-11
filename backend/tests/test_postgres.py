"""Integration checks against a real PostgreSQL (CI service or infra/docker-compose.yml).

Skipped when LKD_TEST_DATABASE_URL is not set.
"""

import os

import pytest
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("LKD_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="LKD_TEST_DATABASE_URL not set")


def test_postgres_is_version_18_with_uuidv7() -> None:
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        major = connection.execute(text("SHOW server_version_num")).scalar_one()
        generated = connection.execute(text("SELECT uuidv7()::text")).scalar_one()
    assert int(major) // 10000 == 18
    assert generated[14] == "7"  # UUID version nibble

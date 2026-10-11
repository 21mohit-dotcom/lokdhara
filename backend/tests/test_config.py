import pytest

from app.config import Settings


def test_settings_read_lkd_prefixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LKD_ENV", "test")
    monkeypatch.setenv("LKD_DATABASE_URL", "postgresql+psycopg://u:p@db:5432/x")
    settings = Settings(_env_file=None)
    assert settings.env == "test"
    assert settings.database_url.endswith("@db:5432/x")


def test_secret_key_is_not_revealed_in_repr() -> None:
    settings = Settings(_env_file=None, secret_key="super-secret-value")
    assert "super-secret-value" not in repr(settings)

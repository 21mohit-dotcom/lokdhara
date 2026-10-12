"""Encryption of restricted speaker identity fields (docs/PRIVACY_AND_SECURITY.md)."""

import base64
import os
import uuid

import pytest

from app.config import Settings
from app.modules.speakers.crypto import DecryptionError, IdentityCipher, identity_cipher

SPEAKER = uuid.uuid4()


def _cipher() -> IdentityCipher:
    return IdentityCipher(os.urandom(32))


def test_round_trip_and_fresh_nonce_each_time() -> None:
    cipher = _cipher()
    first = cipher.encrypt(SPEAKER, "full_name", "Synthetic Name")
    second = cipher.encrypt(SPEAKER, "full_name", "Synthetic Name")
    assert first != second
    assert b"Synthetic" not in first
    assert cipher.decrypt(SPEAKER, "full_name", first, cipher.key_version) == "Synthetic Name"


def test_values_cannot_be_moved_between_columns_or_speakers() -> None:
    cipher = _cipher()
    sealed = cipher.encrypt(SPEAKER, "full_name", "Synthetic Name")
    with pytest.raises(DecryptionError):
        cipher.decrypt(SPEAKER, "contact", sealed, cipher.key_version)
    with pytest.raises(DecryptionError):
        cipher.decrypt(uuid.uuid4(), "full_name", sealed, cipher.key_version)


def test_tampering_and_unknown_key_versions_fail() -> None:
    cipher = _cipher()
    sealed = bytearray(cipher.encrypt(SPEAKER, "notes", "x"))
    sealed[-1] ^= 1
    with pytest.raises(DecryptionError):
        cipher.decrypt(SPEAKER, "notes", bytes(sealed), cipher.key_version)
    with pytest.raises(DecryptionError, match="version"):
        cipher.decrypt(SPEAKER, "notes", bytes(sealed), 99)


def test_configured_key_is_used_and_local_key_is_derived() -> None:
    key = os.urandom(32)
    configured = identity_cipher(
        Settings(_env_file=None, identity_encryption_key=base64.b64encode(key).decode())
    )
    sealed = IdentityCipher(key).encrypt(SPEAKER, "village", "Test Village")
    assert configured.decrypt(SPEAKER, "village", sealed, 1) == "Test Village"

    local = Settings(_env_file=None, env="test", secret_key="test-secret-key-not-for-real-use")
    derived = identity_cipher(local).encrypt(SPEAKER, "village", "Test Village")
    assert identity_cipher(local).decrypt(SPEAKER, "village", derived, 1) == "Test Village"

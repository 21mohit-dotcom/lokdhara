"""Application-level encryption of restricted speaker identity fields.

AES-256-GCM with a random 96-bit nonce per value, stored as nonce || ciphertext. The associated
data binds each value to its speaker, column, and key version, so a ciphertext copied to another
row or column does not decrypt. Plaintext never leaves this module except to the caller.
"""

import os
import uuid

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.config import Settings

KEY_VERSION = 1
_NONCE_BYTES = 12


class DecryptionError(Exception):
    """The value was tampered with, moved, or encrypted under another key."""


class IdentityCipher:
    def __init__(self, key: bytes, key_version: int = KEY_VERSION) -> None:
        if len(key) != 32:
            raise ValueError("identity key must be 32 bytes")
        self._aead = AESGCM(key)
        self.key_version = key_version

    def _associated_data(self, speaker_id: uuid.UUID, column: str) -> bytes:
        return f"speaker_identities:{column}:{speaker_id}:v{self.key_version}".encode()

    def encrypt(self, speaker_id: uuid.UUID, column: str, plaintext: str) -> bytes:
        nonce = os.urandom(_NONCE_BYTES)
        sealed = self._aead.encrypt(
            nonce, plaintext.encode("utf-8"), self._associated_data(speaker_id, column)
        )
        return nonce + sealed

    def decrypt(self, speaker_id: uuid.UUID, column: str, value: bytes, key_version: int) -> str:
        if key_version != self.key_version:
            raise DecryptionError(f"no key for version {key_version}")
        nonce, sealed = value[:_NONCE_BYTES], value[_NONCE_BYTES:]
        try:
            plaintext = self._aead.decrypt(nonce, sealed, self._associated_data(speaker_id, column))
        except InvalidTag as exc:
            raise DecryptionError("identity value failed authentication") from exc
        return plaintext.decode("utf-8")


def identity_cipher(settings: Settings) -> IdentityCipher:
    key = settings.identity_key_bytes()
    if key is None:
        if not settings.is_local:  # also enforced when settings load
            raise RuntimeError("LKD_IDENTITY_ENCRYPTION_KEY is not configured")
        # Development and test only: derived, so local data survives restarts without setup.
        key = HKDF(
            algorithm=hashes.SHA256(), length=32, salt=None, info=b"lokdhara identity key v1"
        ).derive(settings.secret_key.get_secret_value().encode())
    return IdentityCipher(key)

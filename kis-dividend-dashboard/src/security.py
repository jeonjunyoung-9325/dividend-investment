"""Security primitives that never expose secret material in representations or logs."""

from __future__ import annotations

from hashlib import sha256

from cryptography.fernet import Fernet


class TokenCipher:
    """Encrypt and authenticate KIS access tokens with a deployment secret."""

    __slots__ = ("_fernet",)

    def __init__(self, key: str) -> None:
        """Validate and retain only the library cipher object."""
        self._fernet = Fernet(key.encode("ascii"))

    def encrypt(self, plaintext: str) -> bytes:
        """Return authenticated ciphertext suitable for a PostgreSQL BYTEA column."""
        return self._fernet.encrypt(plaintext.encode("utf-8"))

    def decrypt(self, ciphertext: bytes) -> str:
        """Decrypt ciphertext or raise cryptography's non-secret InvalidToken error."""
        return self._fernet.decrypt(ciphertext).decode("utf-8")

    def __repr__(self) -> str:
        """Keep the encryption key out of diagnostic representations."""
        return "TokenCipher(key=<redacted>)"


def app_key_fingerprint(app_key: str) -> str:
    """Create a stable identifier without retaining the App Key itself."""
    if not app_key:
        msg = "App Key must not be empty"
        raise ValueError(msg)
    return sha256(app_key.encode("utf-8")).hexdigest()


def mask_account_number(account_number: str) -> str:
    """Mask an account number while retaining only its first four digits."""
    prefix = account_number.replace("-", "")[:4]
    return f"{prefix}****-**" if prefix else "****-**"
